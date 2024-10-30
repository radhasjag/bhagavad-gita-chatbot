import os
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
import streamlit as st
from utils.monitoring import monitor

class ResponseGenerator:
    def __init__(self):
        try:
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                print("Warning: OpenAI API key is missing!")
                raise ValueError("OpenAI API key is not set in environment")
            print("OpenAI API key is set")
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            print(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
        
    def format_conversation_history(self, conversation):
        """Format the conversation history for the prompt."""
        try:
            if not conversation:
                return ""
            
            formatted_history = "\nPrevious conversation:\n"
            for conv in conversation[-3:]:  # Only include last 3 conversations for context
                formatted_history += f"Seeker: {conv['question']}\n"
                formatted_history += f"Krishna: {conv['short_answer']}\n"
            monitor.log_performance_metric("conversation_history_length", len(formatted_history), {"type": "formatting"})
            return formatted_history
        except Exception as e:
            monitor.log_error("system", e, {"context": "format_conversation_history"})
            return ""

    def format_verses_context(self, relevant_verses):
        """Format the relevant verses for the prompt."""
        try:
            if relevant_verses is None or relevant_verses.empty:
                monitor.log_performance_metric("verses_found", 0, {"type": "verse_processing"})
                return "No specific verses found for this query."
            
            monitor.log_performance_metric("verses_found", len(relevant_verses), {"type": "verse_processing"})
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

    def generate_response(self, question, relevant_verses, context, conversation=[]):
        """Generate both concise and detailed responses in Krishna's voice using OpenAI."""
        try:
            start_time = time.time()
            session_id = str(hash(question))
            monitor.log_interaction(session_id, question)

            if self.client is None:
                raise ValueError("OpenAI client not properly initialized")
            
            if not question or not isinstance(question, str):
                raise ValueError("Invalid question format")
            
            system_prompt = """You are Lord Krishna speaking to a seeker of wisdom through the teachings of Bhagavad Gita. 
            Provide two types of responses:
            
            1. A SHORT ANSWER (2-3 sentences):
            - Direct answer to the question
            - Essential wisdom without verse references
            - Clear, practical guidance
            
            2. A DETAILED EXPLANATION:
            - Elaborate on the short answer
            - Include relevant verse references (BG chapter.verse)
            - Explain how verses apply to the situation
            - Connect with previous discussions
            - Provide practical applications
            
            Use a tone that reflects divine knowledge, compassion, and unconditional love.
            
            Format your response as JSON with two fields:
            {
                "short_answer": "Your concise response here",
                "detailed_explanation": "Your detailed response here"
            }"""
            
            conversation_history = self.format_conversation_history(conversation)
            verses_context = self.format_verses_context(relevant_verses)
            
            user_prompt = f"""Question: {question}

Relevant verses from Bhagavad Gita:
{verses_context}
{conversation_history}

Please provide both a concise answer and detailed explanation using the verses above."""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                
                if not response or not response.choices:
                    raise ValueError("Empty response from OpenAI API")
                
                response_data = json.loads(response.choices[0].message.content)
                
                response_time = time.time() - start_time
                monitor.log_response_metrics(session_id, response_time, True)
                
                return response_data
                
            except (RateLimitError, APIConnectionError, APIError) as api_error:
                monitor.log_error(session_id, api_error, {"context": "api_call"})
                error_response = {
                    "short_answer": "Forgive me, dear one. I need a moment to contemplate. Please try again shortly.",
                    "detailed_explanation": str(api_error)
                }
                return error_response
                
        except Exception as e:
            monitor.log_error(session_id, e, {"context": "generate_response"})
            error_response = {
                "short_answer": "Forgive me, dear one, but I am unable to provide guidance at this moment.",
                "detailed_explanation": f"Technical error: {str(e)}"
            }
            return error_response
