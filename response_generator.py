import os
from openai import OpenAI

class ResponseGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def format_conversation_history(self, conversation):
        """Format the conversation history for the prompt."""
        if not conversation:
            return ""
        
        formatted_history = "\nPrevious conversation:\n"
        for conv in conversation[-3:]:  # Only include last 3 conversations for context
            formatted_history += f"Seeker: {conv['question']}\n"
            formatted_history += f"Krishna: {conv['answer']}\n"
        return formatted_history

    def format_verses_context(self, relevant_verses):
        """Format the relevant verses for the prompt."""
        return "\n".join([
            f"Chapter {verse['chapter']}, Verse {verse['verse_number']}: {verse['verse_text']}\nMeaning: {verse['meaning']}"
            for _, verse in relevant_verses.iterrows()
        ])

    def generate_response(self, question, relevant_verses, context, conversation=[]):
        """Generate a response in Krishna's voice using OpenAI with conversation history."""
        # Create the system prompt
        system_prompt = """You are Lord Krishna speaking to a seeker of wisdom through the teachings of Bhagavad Gita. 
        Respond with deep spiritual wisdom, compassion, and authority, using a tone that reflects divine knowledge and unconditional love.
        Consider the previous conversation context to maintain continuity and provide more personalized guidance.
        Always reference the relevant verses from Bhagavad Gita to support your teachings, and connect your current answer 
        with previous discussions when appropriate."""
        
        # Format conversation history
        conversation_history = self.format_conversation_history(conversation)
        
        # Format verses context
        verses_context = self.format_verses_context(relevant_verses)
        
        user_prompt = f"""Question: {question}

Relevant verses from Bhagavad Gita:
{verses_context}
{conversation_history}

Please provide guidance while maintaining continuity with our previous discussion if any."""
        
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
            
            return response.choices[0].message.content
            
        except Exception as e:
            return "Forgive me, dear one, but I am unable to provide guidance at this moment. Please ask your question again."
