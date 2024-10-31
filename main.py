import streamlit as st
from gita_processor import GitaProcessor
from response_generator import ResponseGenerator
from utils.monitoring import monitor
from utils.production_utils import init_session, rate_limiter, get_health_status, cache_response
import time

def initialize_session_state():
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'context' not in st.session_state:
        st.session_state.context = []

@cache_response
def process_question(question, gita_processor, response_generator, context, conversation):
    """Process user question with caching"""
    relevant_verses = gita_processor.find_relevant_verses(question)
    return response_generator.generate_response(
        question,
        relevant_verses,
        context,
        conversation
    )

def format_metric_value(value):
    """Format metric values to be more readable"""
    if isinstance(value, float):
        if value < 0.01:  # For very small numbers
            return f"{value:.4f}"
        return f"{value:.2f}"
    elif isinstance(value, int):
        return f"{value:,}"  # Add thousands separator
    return str(value)

def main():
    # Custom CSS for sidebar styling
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            background-color: #FFF3E0;
            padding: 2rem 1rem;
        }
        .metric-container {
            background-color: white;
            padding: 1.5rem;
            margin: 1.2rem 0;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            border-left: 4px solid #FF9933;
        }
        .metric-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .metric-value {
            font-size: 1.4rem;
            font-weight: 700;
            color: #FF9933;
            padding-left: 1.5rem;
        }
        .health-status {
            margin-top: 2rem;
            padding: 1.5rem;
            border-radius: 8px;
            background-color: white;
            border-left: 4px solid #28a745;
        }
        .status-healthy {
            color: #28a745;
        }
        .status-degraded {
            color: #ffc107;
            border-left-color: #ffc107;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🕉️ Bhagavad Gita Wisdom with Sri Krishna")
    
    # Initialize session and state
    initialize_session_state()
    session_id = init_session()
    
    # Initialize processors
    gita_processor = GitaProcessor()
    response_generator = ResponseGenerator()

    # Sidebar Metrics Display
    st.sidebar.markdown("## System Metrics Dashboard")
    metrics = monitor.get_metrics()
    
    # Metrics with simple text-based icons
    metric_icons = {
        'total_interactions': '[>]',
        'successful_responses': '[+]',
        'failed_responses': '[!]',
        'avg_response_time': '[~]',
        'active_sessions': '[*]',
    }
    
    for metric, value in metrics.items():
        icon = metric_icons.get(metric, '[#]')
        formatted_value = format_metric_value(value)
        metric_name = metric.replace('_', ' ').title()
        
        st.sidebar.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">{icon} {metric_name}</div>
                <div class="metric-value">{formatted_value}</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Health Status Display
    health_status = get_health_status()
    st.sidebar.markdown("### System Health Status")
    status_class = "status-healthy" if health_status["status"] == "healthy" else "status-degraded"
    status_icon = "[OK]" if health_status["status"] == "healthy" else "[!!]"
    
    st.sidebar.markdown(f"""
        <div class="health-status {status_class}">
            <div class="metric-title">
                {status_icon} Status: {health_status["status"].title()}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar.expander("View Health Details"):
        st.json(health_status)
    
    # Add a spiritual background description
    st.markdown("""
    *Welcome, seeker of wisdom. I am Krishna, your guide through the eternal teachings 
    of the Bhagavad Gita. Ask your questions, and I shall illuminate the path.*
    """)
    
    # Add follow-up questions explanation using Streamlit components
    st.markdown("### 💫 Continuous Dialogue Feature")
    
    st.markdown("""
    Our conversation is a continuous journey of wisdom. You can ask follow-up questions, 
    and I will maintain the context of our discussion, just as I did with Arjuna on the 
    battlefield of Kurukshetra.
    """)
    
    # Example container with custom styling
    st.markdown("#### Examples of Questions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Starting Question:**
        "What is the main message of Bhagavad Gita?"
        
        **Career Guidance:**
        "Should I quit my job to pursue a startup?"
        """)
    
    with col2:
        st.info("""
        **Self-Discovery:**
        "What is dharma and how do I follow it?"
        
        **Follow-up:**
        "How can I balance my responsibilities?"
        """)
    
    st.markdown("""
    💡 *Each response includes both a concise answer and a detailed explanation with relevant verses. 
    Click "detailed explanation" to see the complete response with verse references.*
    """)
    
    # Display conversation history before the input box
    if st.session_state.conversation:
        st.subheader("Our Conversation")
        for idx, conv in enumerate(st.session_state.conversation):
            with st.container():
                st.text_area(f"You asked:", conv["question"], height=50, disabled=True, key=f"q_{idx}")
                st.markdown(f"**Krishna's Wisdom:**\n{conv['short_answer']}")
                
                with st.expander("Click for detailed explanation with verses"):
                    st.markdown(conv['detailed_explanation'])
                st.markdown("---")
    
    # User input box now appears after the conversation history
    user_question = st.text_input("What wisdom do you seek?", key="user_input")
    
    if user_question:
        # Check rate limit
        if not rate_limiter.is_allowed(session_id):
            st.warning("Please wait a moment before asking another question.")
            return
        
        try:
            start_time = time.time()
            
            # Process the question and generate response
            response_data = process_question(
                user_question,
                gita_processor,
                response_generator,
                st.session_state.context,
                st.session_state.conversation
            )
            
            # Add to conversation history
            st.session_state.conversation.append({
                "question": user_question,
                "short_answer": response_data["short_answer"],
                "detailed_explanation": response_data["detailed_explanation"]
            })
            
            # Log performance metrics
            response_time = time.time() - start_time
            monitor.log_performance_metric(
                "total_response_time",
                response_time,
                {"question_length": len(user_question), "session_id": session_id}
            )
            
            # Update rerun command to use st.rerun() instead of st.experimental_rerun()
            st.rerun()
            
        except Exception as e:
            monitor.log_error(session_id, e, {"context": "main_execution"})
            st.error("Forgive me, dear one. I am unable to provide guidance at this moment. Please try again.")

if __name__ == "__main__":
    main()
