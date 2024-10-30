import os
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
import streamlit as st

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
                formatted_history += f"Krishna: {conv['answer']}\n"
            print(f"Conversation history formatted successfully, length: {len(formatted_history)}")
            return formatted_history
        except Exception as e:
            print(f"Error formatting conversation history: {str(e)}")
            return ""

    def format_verses_context(self, relevant_verses):
        """Format the relevant verses for the prompt."""
        try:
            if relevant_verses is None or relevant_verses.empty:
                print("Warning: No relevant verses found")
                return "No specific verses found for this query."
            
            print(f"Number of relevant verses found: {len(relevant_verses)}")
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
                    print(f"Error: Missing required column in verse data: {ke}")
                    continue
                
            verses_text = "\n\n".join(formatted_verses)
            print(f"Verses context formatted successfully, length: {len(verses_text)}")
            return verses_text
        except Exception as e:
            print(f"Error formatting verses context: {str(e)}")
            return "Error processing verses."

    def generate_response(self, question, relevant_verses, context, conversation=[]):
        """Generate a response in Krishna's voice using OpenAI with conversation history."""
        try:
            # Verify client initialization
            if self.client is None:
                raise ValueError("OpenAI client not properly initialized")
            
            # Verify inputs
            if not question or not isinstance(question, str):
                raise ValueError("Invalid question format")
            
            print(f"Processing question: {question}")
            
            # Create the system prompt with enhanced verse reference instructions
            system_prompt = """You are Lord Krishna speaking to a seeker of wisdom through the teachings of Bhagavad Gita. 
            Follow these guidelines for your response:
            1. Begin with a direct answer to the seeker's question
            2. Support your answer with specific verse references using the format (BG chapter.verse)
            3. Explain how each verse applies to the seeker's situation
            4. Connect your current answer with previous discussions when relevant
            5. End with a practical application or specific guidance
            
            Use a tone that reflects divine knowledge, compassion, and unconditional love."""
            
            # Format conversation history
            conversation_history = self.format_conversation_history(conversation)
            if conversation_history:
                print("Conversation history validation passed")
            
            # Format verses context
            verses_context = self.format_verses_context(relevant_verses)
            if verses_context == "Error processing verses.":
                raise ValueError("Failed to process verses context")
            
            user_prompt = f"""Question: {question}

Relevant verses from Bhagavad Gita:
{verses_context}
{conversation_history}

Please provide guidance using the specific verses given above, and ensure to reference them in your response using the format (BG chapter.verse). Make the connection between the verses and the seeker's question clear and practical."""

            # Print debug information
            print(f"Total prompt length: {len(system_prompt) + len(user_prompt)}")
            print("Preparing to send request to OpenAI API...")
            
            # Make the API call
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=750  # Increased to accommodate verse references
                )
                print("OpenAI API request completed successfully")
                
                if not response or not response.choices:
                    raise ValueError("Empty response from OpenAI API")
                
                # Format the response to highlight verse references
                answer = response.choices[0].message.content
                
                # Add a clear separator for verse references if they exist
                if any(f"BG {i}" in answer for i in range(1, 19)):
                    answer += "\n\n---\n*References from Bhagavad Gita are indicated as (BG chapter.verse)*"
                
                return answer
                
            except RateLimitError as rle:
                print(f"OpenAI API rate limit exceeded: {str(rle)}")
                return "Forgive me, dear one. I need a moment to contemplate. Please try again shortly."
            except APIConnectionError as ace:
                print(f"OpenAI API connection error: {str(ace)}")
                return "Forgive me, but I am unable to connect with the divine wisdom at this moment. Please try again."
            except APIError as ae:
                print(f"OpenAI API error: {str(ae)}")
                return "Forgive me, there seems to be a disturbance in our connection. Please ask your question again."
                
        except ValueError as ve:
            print(f"Validation Error: {str(ve)}")
            return "Forgive me, dear one, but I need a clear question to provide guidance."
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            return "Forgive me, dear one, but I am unable to provide guidance at this moment. Please ask your question again."
