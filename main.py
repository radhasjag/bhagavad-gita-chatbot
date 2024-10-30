import streamlit as st
from gita_processor import GitaProcessor
from response_generator import ResponseGenerator
from utils.monitoring import monitor
import time

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
            start_time = time.time()
            
            # Process the question and generate response
            relevant_verses = gita_processor.find_relevant_verses(user_question)
            response_data = response_generator.generate_response(
                user_question, 
                relevant_verses,
                st.session_state.context,
                st.session_state.conversation
            )
            
            # Add to conversation history
            st.session_state.conversation.append({
                "question": user_question,
                "short_answer": response_data["short_answer"],
                "detailed_explanation": response_data["detailed_explanation"]
            })
            st.session_state.context.append(relevant_verses)
            
            # Display conversation history
            st.subheader("Our Conversation")
            for idx, conv in enumerate(st.session_state.conversation):
                with st.container():
                    st.text_area(f"You asked:", conv["question"], height=50, disabled=True, key=f"q_{idx}")
                    st.markdown(f"**Krishna's Wisdom:**\n{conv['short_answer']}")
                    
                    with st.expander("Click for detailed explanation with verses"):
                        st.markdown(conv['detailed_explanation'])
                    st.markdown("---")
            
            # Log performance metrics
            response_time = time.time() - start_time
            monitor.log_performance_metric("total_response_time", response_time, 
                                        {"question_length": len(user_question)})
            
        except Exception as e:
            monitor.log_error("system", e, {"context": "main_execution"})
            st.error("Forgive me, dear one. I am unable to provide guidance at this moment. Please try again.")
            print(f"Error: {str(e)}")  # For debugging purposes

    # Display monitoring metrics in sidebar if requested
    if st.sidebar.checkbox("Show Monitoring Metrics"):
        metrics = monitor.get_metrics()
        st.sidebar.subheader("System Metrics")
        for metric, value in metrics.items():
            st.sidebar.metric(label=metric.replace('_', ' ').title(), value=value)

if __name__ == "__main__":
    main()
