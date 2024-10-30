import os
from openai import OpenAI
from openai.types.error import APIError, APIConnectionError, RateLimitError

class ResponseGenerator:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OpenAI API key is missing!")
        else:
            print("OpenAI API key is set")
        self.client = OpenAI(api_key=self.api_key)
        
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
                    formatted_verse = f"Chapter {verse['chapter']}, Verse {verse['verse_number']}: {verse['verse_text']}\nMeaning: {verse['meaning']}"
                    formatted_verses.append(formatted_verse)
                except KeyError as ke:
                    print(f"Error: Missing required column in verse data: {ke}")
                    continue
                
            verses_text = "\n".join(formatted_verses)
            print(f"Verses context formatted successfully, length: {len(verses_text)}")
            return verses_text
        except Exception as e:
            print(f"Error formatting verses context: {str(e)}")
            return "Error processing verses."

    def generate_response(self, question, relevant_verses, context, conversation=[]):
        """Generate a response in Krishna's voice using OpenAI with conversation history."""
        try:
            # Verify API key
            if not self.api_key:
                raise ValueError("OpenAI API key is missing")
            
            # Verify inputs
            if not question or not isinstance(question, str):
                raise ValueError("Invalid question format")
            
            print(f"Processing question: {question}")
            
            # Create the system prompt
            system_prompt = """You are Lord Krishna speaking to a seeker of wisdom through the teachings of Bhagavad Gita. 
            Respond with deep spiritual wisdom, compassion, and authority, using a tone that reflects divine knowledge and unconditional love.
            Consider the previous conversation context to maintain continuity and provide more personalized guidance.
            Always reference the relevant verses from Bhagavad Gita to support your teachings, and connect your current answer 
            with previous discussions when appropriate."""
            
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

Please provide guidance while maintaining continuity with our previous discussion if any."""

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
                    max_tokens=500
                )
                print("OpenAI API request completed successfully")
                
                if not response or not response.choices:
                    raise ValueError("Empty response from OpenAI API")
                    
                return response.choices[0].message.content
                
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
