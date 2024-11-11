import streamlit as st
from gita_processor import GitaProcessor
from response_generator import ResponseGenerator
from utils.monitoring import monitor
from utils.production_utils import init_session, rate_limiter, get_health_status, cache_response
import time

# Constants
MAX_CONVERSATION_LENGTH = 50
MAX_QUESTION_LENGTH = 500


def initialize_session_state():
    """Initialize all session state variables"""
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'context' not in st.session_state:
        st.session_state.context = []
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "error" not in st.session_state:
        st.session_state.error = None
    if 'question_processed' not in st.session_state:
        st.session_state.question_processed = False
    if 'last_processed_question' not in st.session_state:
        st.session_state.last_processed_question = None


@cache_response
def process_question(question, gita_processor, response_generator, context,
                     conversation):
    """Process user question with caching and validation"""
    try:
        # Input validation
        if not question.strip() or len(question) > MAX_QUESTION_LENGTH:
            raise ValueError("Invalid question length")

        relevant_verses = gita_processor.find_relevant_verses(question)
        response = response_generator.generate_response(
            question, relevant_verses, context, conversation)

        # Response validation
        if not isinstance(response, dict) or \
           not all(key in response for key in ['short_answer', 'detailed_explanation']):
            raise ValueError("Invalid response format")

        return response
    except Exception as e:
        monitor.log_error("system", e, {
            "context": "process_question",
            "question_length": len(question)
        })
        raise


def format_metric_value(value):
    """Format metric values to be more readable"""
    if isinstance(value, float):
        return f"{value:.4f}" if value < 0.01 else f"{value:.2f}"
    elif isinstance(value, int):
        return f"{value:,}"
    return str(value)


def display_conversation_history():
    """Display conversation history in chronological order"""
    if st.session_state.conversation:
        st.subheader("Our Conversation")
        displayed_questions = set()

        # Use the original order (not reversed)
        for conv in st.session_state.conversation:
            # Skip duplicates
            if conv["question"] in displayed_questions:
                continue

            displayed_questions.add(conv["question"])

            with st.container():
                # Question container with light background
                with st.container():
                    st.markdown("""
                        <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem;">
                            <small style="color: #6c757d;">You asked:</small>
                            <div style="margin-top: 0.5rem;">
                                %s
                            </div>
                        </div>
                    """ % conv["question"],
                                unsafe_allow_html=True)

                # Response container
                with st.container():
                    st.markdown("""
                        <div style="margin-left: 1rem;">
                            <strong>Krishna's Wisdom:</strong>
                            <div style="margin-top: 0.5rem;">
                                %s
                            </div>
                        </div>
                    """ % conv["short_answer"],
                                unsafe_allow_html=True)

                    with st.expander(
                            "Click for detailed explanation with verses"):
                        st.markdown(conv["detailed_explanation"])

                # Separator
                st.markdown("<hr style='margin: 2rem 0; opacity: 0.2;'>",
                            unsafe_allow_html=True)


def handle_user_input(user_question, session_id, gita_processor,
                      response_generator):
    """Handle user input with proper error handling and state management"""
    try:
        # Prevent duplicate processing
        if 'last_processed_question' in st.session_state and \
           st.session_state.last_processed_question == user_question:
            return

        # Check rate limit before processing
        if not rate_limiter.is_allowed(session_id):
            st.warning(
                "🕉️ Please wait a moment before asking another question.")
            return

        st.session_state.processing = True
        start_time = time.time()

        # Manage conversation length
        if len(st.session_state.conversation) >= MAX_CONVERSATION_LENGTH:
            st.session_state.conversation.pop(0)

        try:
            # Your response generation code here
            response_data = process_question(user_question, gita_processor,
                                             response_generator,
                                             st.session_state.context,
                                             st.session_state.conversation)
            monitor.log_response_metrics(session_id,
                                         time.time() - start_time, True)

            # Update conversation with new Q&A
            st.session_state.last_processed_question = user_question
            st.session_state.conversation.append({
                "question":
                user_question,
                "short_answer":
                response_data["short_answer"],
                "detailed_explanation":
                response_data["detailed_explanation"],
                "id":
                len(st.session_state.conversation)  # Add unique ID
            })
        except Exception as e:
            monitor.log_response_metrics(session_id,
                                         time.time() - start_time, False,
                                         str(e))

        # Log success metrics
        response_time = time.time() - start_time
        monitor.log_performance_metric("total_response_time", response_time, {
            "question_length": len(user_question),
            "session_id": session_id
        })

        st.session_state.question_processed = True

    except Exception as e:
        error_msg = "Forgive me, dear one. I am unable to provide guidance at this moment. Please try again."
        st.error(error_msg)
        monitor.log_error(session_id, e, {"context": "handle_user_input"})
    finally:
        st.session_state.processing = False


def display_selected_metrics():
    """Display only selected metrics in the sidebar"""
    st.sidebar.markdown("## System Metrics Dashboard")

    # Define selected metrics and their display properties
    selected_metrics = {
        'total_interactions': {
            'icon': '[>]',
            'label': 'Total Interactions',
            'format': lambda x: f"{x:,}"  # Format as integer with commas
        },
        'successful_responses': {
            'icon': '[+]',
            'label': 'Successful Responses',
            'format': lambda x: f"{x:,}"
        },
        'failed_responses': {
            'icon': '[!]',
            'label': 'Failed Responses',
            'format': lambda x: f"{x:,}"
        },
        'avg_response_time': {
            'icon': '[~]',
            'label': 'Avg Response Time',
            'format': lambda x: f"{x:.2f}s"
            if x else "0.00s"  # Format as seconds with 2 decimal places
        }
    }

    # Get current metrics
    metrics = monitor.get_metrics()

    # Custom CSS for metrics display
    st.markdown("""
        <style>
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
        </style>
    """,
                unsafe_allow_html=True)

    # Display only selected metrics
    for metric_key, properties in selected_metrics.items():
        value = metrics.get(metric_key, 0)
        formatted_value = properties['format'](value)

        st.sidebar.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">{properties['icon']} {properties['label']}</div>
                <div class="metric-value">{formatted_value}</div>
            </div>
        """,
                            unsafe_allow_html=True)


def main():
    try:
        initialize_session_state()
        session_id = init_session()

        # Initialize processors
        gita_processor = GitaProcessor()
        response_generator = ResponseGenerator()

        st.title("🕉️ Bhagavad Gita Wisdom with Sri Krishna")

        # Display metrics
        display_selected_metrics()

        # Add a spiritual background description
        st.markdown("""
        *Welcome, seeker of wisdom. I am Krishna, your guide through the eternal teachings 
        of the Bhagavad Gita. Ask your questions, and I shall illuminate the path.*
        """)

        # Add dialogue feature explanation
        st.markdown("### 💫 Continuous Dialogue Feature")
        st.markdown("""
        Our conversation is a continuous journey of wisdom. You can ask follow-up questions, 
        and I will maintain the context of our discussion, just as I did with Arjuna on the 
        battlefield of Kurukshetra.
        """)

        # User input form - Place it BEFORE the conversation display
        with st.form(key='question_form', clear_on_submit=True):
            user_question = st.text_input("What wisdom do you seek?",
                                          key="user_input",
                                          disabled=st.session_state.processing,
                                          max_chars=MAX_QUESTION_LENGTH)
            submit_button = st.form_submit_button("Ask Krishna")

        if st.session_state.processing:
            st.info("🕉️ Krishna is contemplating your question...")

        # Handle form submission
        if submit_button and user_question:
            handle_user_input(user_question, session_id, gita_processor,
                              response_generator)

            if st.session_state.question_processed:
                st.session_state.question_processed = False
                time.sleep(0.1)  # Small delay to ensure state is updated
                st.rerun()

        # Display conversation history
        display_conversation_history()

    except Exception as e:
        monitor.log_error("system", e, {"context": "main_function"})
        st.error(
            "The system is experiencing difficulties. Please try again later.")


if __name__ == "__main__":
    main()
