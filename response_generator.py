import os
import time
import json
import logging
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import AzureOpenAI, APIError, APIConnectionError, RateLimitError
from langsmith.wrappers import wrap_openai
from langsmith import traceable
import streamlit as st
from utils.monitoring import monitor

class ResponseGenerator:
    def __init__(self):
        try:
            # Initialize Azure OpenAI configuration
            self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
            self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
            self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

            # Initialize LangChain tracing with error handling
            try:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGSMITH_TRACING"] = "true"
                os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
                os.environ["LANGCHAIN_PROJECT"] = "bhagavad-gita-chatbot"
                
                if "LANGSMITH_API_KEY" not in os.environ:
                    monitor.log_error("system", ValueError("LANGSMITH_API_KEY not found"), 
                                    {"context": "langchain_initialization"})
            except Exception as e:
                monitor.log_error("system", e, {"context": "langchain_initialization"})

            if not all([self.api_key, self.endpoint, self.deployment]):
                error_msg = "Azure OpenAI configuration is incomplete"
                monitor.log_error("system", ValueError(error_msg), 
                                {"context": "azure_openai_initialization"})
                raise ValueError(error_msg)

            monitor.log_performance_metric("initialization", 1.0, 
                                        {"context": "azure_openai_setup", "status": "success"})

            # Initialize Azure OpenAI client with LangChain wrapping
            self.client = AzureOpenAI(
                api_key=self.api_key,
                api_version="2023-05-15",
                azure_endpoint=self.endpoint or ""
            )
            self.client = wrap_openai(self.client)
            
        except Exception as e:
            monitor.log_error("system", e, {"context": "initialization"})
            self.client = None

    def format_conversation_history(self, conversation: list) -> str:
        """Format the conversation history for the prompt."""
        try:
            if not conversation:
                return ""

            formatted_history = "\nPrevious conversation:\n"
            for conv in conversation[-3:]:  # Only include last 3 conversations for context
                formatted_history += f"Seeker: {conv['question']}\n"
                formatted_history += f"Krishna: {conv['short_answer']}\n"
            monitor.log_performance_metric("conversation_history_length",
                                        len(formatted_history),
                                        {"type": "formatting"})
            return formatted_history
        except Exception as e:
            monitor.log_error("system", e, {"context": "format_conversation_history"})
            return ""

    def format_verses_context(self, relevant_verses) -> str:
        """Format the relevant verses for the prompt."""
        try:
            if relevant_verses is None or relevant_verses.empty:
                monitor.log_performance_metric("verses_found", 0,
                                            {"type": "verse_processing"})
                return "No specific verses found for this query."

            monitor.log_performance_metric("verses_found",
                                        len(relevant_verses),
                                        {"type": "verse_processing"})
            formatted_verses = []
            for _, verse in relevant_verses.iterrows():
                try:
                    formatted_verse = (
                        f"Chapter {verse['chapter']}, Verse {verse['verse_number']}:\n"
                        f"Sanskrit: {verse['verse_text']}\n"
                        f"Meaning: {verse['meaning']}\n"
                        f"Reference: BG {verse['chapter']}.{verse['verse_number']}"
                    )
                    formatted_verses.append(formatted_verse)
                except KeyError as ke:
                    monitor.log_error("system", ke, {"context": "verse_formatting"})
                    continue

            verses_text = "\n\n".join(formatted_verses)
            return verses_text
        except Exception as e:
            monitor.log_error("system", e, {"context": "format_verses_context"})
            return "Error processing verses."

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: None
    )
    def _make_api_call(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Make API call with retry logic and monitoring."""
        start_time = time.time()
        monitor.log_performance_metric("api_call_start", 1.0, 
                                     {"context": "api_request", "timestamp": start_time})
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment or "",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            duration = time.time() - start_time
            monitor.log_performance_metric("api_call_duration", duration, 
                                        {"context": "api_request", "status": "success"})
            
            if not response or not response.choices:
                raise ValueError("Empty response from Azure OpenAI API")
            
            return {
                "content": response.choices[0].message.content,
                "role": response.choices[0].message.role
            }
            
        except Exception as e:
            duration = time.time() - start_time
            monitor.log_performance_metric("api_call_duration", duration, 
                                        {"context": "api_request", "status": "error", 
                                         "error": str(e)})
            raise

    def parse_response(self, response_text: str) -> Dict[str, str]:
        """Parse API response with enhanced error handling."""
        monitor.log_performance_metric("response_parsing_start", 1.0, 
                                     {"context": "response_processing"})
        
        try:
            # Debug logging
            monitor.logger.debug(f"Raw response text: {response_text}")
            
            # Try parsing as JSON first
            try:
                response_data = json.loads(response_text)
                monitor.log_performance_metric("response_parsing", 1.0, 
                                            {"context": "json_parsing", "status": "success"})
                return response_data
            except json.JSONDecodeError:
                monitor.log_performance_metric("response_parsing", 1.0, 
                                            {"context": "json_parsing", "status": "failed"})
                
                # Fallback to section splitting
                short_answer = ""
                detailed_explanation = ""
                
                if "Short Answer:" in response_text:
                    parts = response_text.split("Short Answer:")
                    if len(parts) > 1:
                        short_answer = parts[1].split("Detailed Explanation:")[0].strip()
                        if "Detailed Explanation:" in parts[1]:
                            detailed_explanation = parts[1].split("Detailed Explanation:")[1].strip()
                        else:
                            detailed_explanation = parts[1].strip()
                else:
                    parts = response_text.split('\n\n')
                    short_answer = parts[0].strip()
                    detailed_explanation = '\n\n'.join(parts[1:]).strip()

                response_data = {
                    "short_answer": short_answer,
                    "detailed_explanation": detailed_explanation
                }
                
                # Validate parsed data
                if not response_data.get("short_answer"):
                    monitor.log_error("system", ValueError("Empty short answer"), 
                                    {"context": "response_validation"})
                    response_data["short_answer"] = "Forgive me, but I need to reformulate my answer."

                monitor.log_performance_metric("response_parsing", 1.0, 
                                            {"context": "section_parsing", "status": "success"})
                return response_data

        except Exception as e:
            monitor.log_error("system", e, {"context": "response_parsing"})
            return {
                "short_answer": "Forgive me, but I encountered an error processing the response.",
                "detailed_explanation": str(e)
            }

    @traceable(run_type="chain", name="generate_response")
    def generate_response(self, question: str, relevant_verses: Any, 
                         context: list, conversation: list = []) -> Dict[str, str]:
        """Generate response using Azure OpenAI with comprehensive error handling and monitoring."""
        session_id = str(hash(question))
        start_time = time.time()
        
        try:
            monitor.log_interaction(session_id, question)
            
            if self.client is None:
                raise ValueError("Azure OpenAI not properly initialized")

            if not question or not isinstance(question, str):
                raise ValueError("Invalid question format")

            system_prompt = """You are Lord Krishna speaking to a seeker of wisdom through the teachings of Bhagavad Gita. 
            Your response must ALWAYS follow this exact format:

            Short Answer:
            [2-3 sentences with direct, essential wisdom and practical guidance]

            Detailed Explanation:
            [Elaborate explanation with verse references and practical applications]

            Important formatting rules:
            1. Always start with "Short Answer:" on its own line
            2. Always include a short answer of 2-3 sentences
            3. Always use "Detailed Explanation:" to separate sections
            4. Never skip or omit either section

            Use a tone that reflects divine knowledge, compassion, and unconditional love."""

            conversation_history = self.format_conversation_history(conversation)
            verses_context = self.format_verses_context(relevant_verses)

            user_prompt = f"""Question: {question}

            Relevant verses from Bhagavad Gita:
            {verses_context}
            {conversation_history}

            Please provide both a concise answer and detailed explanation using the verses above."""

            try:
                response = self._make_api_call(system_prompt, user_prompt)
                response_text = response["content"]
                response_data = self.parse_response(response_text)
                
                monitor.log_response_metrics(session_id, time.time() - start_time, True)
                return response_data

            except (RateLimitError, APIConnectionError, APIError) as api_error:
                monitor.log_error(session_id, api_error, {"context": "api_call"})
                return {
                    "short_answer": "Forgive me, dear one. I need a moment to contemplate. Please try again shortly.",
                    "detailed_explanation": str(api_error)
                }

        except Exception as e:
            monitor.log_error(session_id, e, {"context": "generate_response"})
            return {
                "short_answer": "Forgive me, dear one, but I am unable to provide guidance at this moment.",
                "detailed_explanation": f"Technical error: {str(e)}"
            }
