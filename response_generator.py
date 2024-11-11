import os
import time
import json
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

            # Initialize LangChain tracing
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ[
                "LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_PROJECT"] = "bhagavad-gita-chatbot"

            if not all([self.api_key, self.endpoint, self.deployment]):
                print("Warning: Azure OpenAI configuration is missing!")
                raise ValueError("Azure OpenAI configuration is not complete")

            print("Azure OpenAI configuration is set")

            # Initialize both Azure OpenAI and LangChain clients
            self.client = AzureOpenAI(api_key=self.api_key,
                                      api_version="2023-05-15",
                                      azure_endpoint=self.endpoint)
            self.client = wrap_openai(self.client)
        except Exception as e:
            print(f"Error initializing Azure OpenAI client: {str(e)}")
            self.client = None

    def format_conversation_history(self, conversation):
        """Format the conversation history for the prompt."""
        try:
            if not conversation:
                return ""

            formatted_history = "\nPrevious conversation:\n"
            for conv in conversation[
                    -3:]:  # Only include last 3 conversations for context
                formatted_history += f"Seeker: {conv['question']}\n"
                formatted_history += f"Krishna: {conv['short_answer']}\n"
            monitor.log_performance_metric("conversation_history_length",
                                           len(formatted_history),
                                           {"type": "formatting"})
            return formatted_history
        except Exception as e:
            monitor.log_error("system", e,
                              {"context": "format_conversation_history"})
            return ""

    def format_verses_context(self, relevant_verses):
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
                    monitor.log_error("system", ke,
                                      {"context": "verse_formatting"})
                    continue

            verses_text = "\n\n".join(formatted_verses)
            return verses_text
        except Exception as e:
            monitor.log_error("system", e,
                              {"context": "format_verses_context"})
            return "Error processing verses."

    @traceable(run_type="chain", project="bhagavad-gita-chatbot")
    def generate_response(self,
                          question,
                          relevant_verses,
                          context,
                          conversation=[]):
        """Generate both concise and detailed responses in Krishna's voice using Azure OpenAI."""
        session_id = str(hash(question))

        try:
            start_time = time.time()
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

            conversation_history = self.format_conversation_history(
                conversation)
            verses_context = self.format_verses_context(relevant_verses)

            user_prompt = f"""Question: {question}

Relevant verses from Bhagavad Gita:
{verses_context}
{conversation_history}

Please provide both a concise answer and detailed explanation using the verses above."""

            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[{
                        "role": "system",
                        "content": system_prompt
                    }, {
                        "role": "user",
                        "content": user_prompt
                    }],
                    temperature=0.7,
                    max_tokens=1000)

                if not response or not response.choices:
                    raise ValueError("Empty response from Azure OpenAI API")

                response_text = response.choices[0].message.content

                # Add debug logging
                print(f"Raw response text: {response_text}")

                # Improved response parsing
                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # Split by sections more reliably
                    if "Short Answer:" in response_text:
                        parts = response_text.split("Short Answer:")
                        if len(parts) > 1:
                            short_answer = parts[1].split(
                                "Detailed Explanation:")[0].strip()
                            detailed_explanation = parts[1].split(
                                "Detailed Explanation:")[1].strip(
                                ) if "Detailed Explanation:" in parts[
                                    1] else parts[1]
                    else:
                        parts = response_text.split('\n\n')
                        short_answer = parts[0].strip()
                        detailed_explanation = '\n\n'.join(parts[1:]).strip()

                    response_data = {
                        "short_answer": short_answer,
                        "detailed_explanation": detailed_explanation
                    }

                # Validate response data
                if not response_data.get("short_answer"):
                    print("Warning: Empty short answer detected")
                    print(f"Response data: {response_data}")
                    response_data[
                        "short_answer"] = "Forgive me, but I need to reformulate my answer."

                # Add debug logging
                print(f"Parsed response data: {response_data}")

                return response_data

            except (RateLimitError, APIConnectionError, APIError) as api_error:
                monitor.log_error(session_id, api_error,
                                  {"context": "api_call"})
                error_response = {
                    "short_answer":
                    "Forgive me, dear one. I need a moment to contemplate. Please try again shortly.",
                    "detailed_explanation": str(api_error)
                }
                return error_response

        except Exception as e:
            monitor.log_error(session_id, e, {"context": "generate_response"})
            error_response = {
                "short_answer":
                "Forgive me, dear one, but I am unable to provide guidance at this moment.",
                "detailed_explanation": f"Technical error: {str(e)}"
            }
            return error_response
