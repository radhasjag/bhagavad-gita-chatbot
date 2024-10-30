import streamlit as st
from gita_processor import GitaProcessor
from response_generator import ResponseGenerator

def initialize_session_state():
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'context' not in st.session_state:
        st.session_state.context = []

def main():
    st.title("🕉️ Bhagavad Gita Wisdom with Srikrishna")
    
    initialize_session_state()
    
    # Initialize processors
    gita_processor = GitaProcessor()
    response_generator = ResponseGenerator()
    
    # Add a spiritual background description
    st.markdown("""
    *Welcome, seeker of wisdom. I am Krishna, your guide through the eternal teachings 
    of the Bhagavad Gita. Ask your questions, and I shall illuminate the path.*
    """)
    
    # User input
    user_question = st.text_input("What wisdom do you seek?", key="user_input")
    
    if user_question:
        try:
            # Process the question and generate response
            relevant_verses = gita_processor.find_relevant_verses(user_question)
            response = response_generator.generate_response(
                user_question, 
                relevant_verses,
                st.session_state.context,
                st.session_state.conversation  # Pass the conversation history
            )
            
            # Add to conversation history
            st.session_state.conversation.append({
                "question": user_question,
                "answer": response
            })
            st.session_state.context.append(relevant_verses)
            
            # Display conversation history
            st.subheader("Our Conversation")
            for idx, conv in enumerate(st.session_state.conversation):
                with st.container():
                    st.text_area(f"You asked:", conv["question"], height=50, disabled=True, key=f"q_{idx}")
                    st.markdown(f"**Krishna says:**\n{conv['answer']}")
                    st.markdown("---")
        
        except Exception as e:
            st.error("Forgive me, dear one. I am unable to provide guidance at this moment. Please try again.")
            print(f"Error: {str(e)}")  # For debugging purposes

if __name__ == "__main__":
    main()
