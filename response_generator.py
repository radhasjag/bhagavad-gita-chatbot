import os
from openai import OpenAI

class ResponseGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def generate_response(self, question, relevant_verses, context):
        """Generate a response in Krishna's voice using OpenAI."""
        # Create the system prompt
        system_prompt = """You are Lord Krishna speaking to a seeker of wisdom through the teachings of Bhagavad Gita. 
        Respond with deep spiritual wisdom, compassion, and authority, using a tone that reflects divine knowledge and unconditional love.
        Always reference the relevant verses from Bhagavad Gita to support your teachings."""
        
        # Create the user prompt with context
        verses_context = "\n".join([
            f"Chapter {verse['chapter']}, Verse {verse['verse_number']}: {verse['verse_text']}\nMeaning: {verse['meaning']}"
            for _, verse in relevant_verses.iterrows()
        ])
        
        user_prompt = f"""Question: {question}\n\nRelevant verses from Bhagavad Gita:\n{verses_context}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return "Forgive me, dear one, but I am unable to provide guidance at this moment. Please ask your question again."
