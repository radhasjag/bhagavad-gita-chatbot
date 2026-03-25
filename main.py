import streamlit as st
from gita_processor import GitaProcessor
from response_generator import ResponseGenerator
from utils.monitoring import monitor
from utils.production_utils import init_session, rate_limiter, cache_response
import time
import base64
import json
import os

# Counter file path
COUNTER_FILE = "query_counter.json"
BASE_COUNT = 6129  # Manual count before automatic tracking


def get_query_count():
    """Get the current query count"""
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "r") as f:
                data = json.load(f)
                return data.get("count", 0) + BASE_COUNT
        return BASE_COUNT
    except Exception:
        return BASE_COUNT


def increment_query_count():
    """Increment the query count"""
    try:
        count = 0
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "r") as f:
                data = json.load(f)
                count = data.get("count", 0)
        count += 1
        with open(COUNTER_FILE, "w") as f:
            json.dump({"count": count}, f)
        return count + BASE_COUNT
    except Exception:
        return BASE_COUNT


def get_base64_image(image_path):
    """Load image and convert to base64 for CSS background"""
    try:
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{data}"
    except Exception:
        return None

# Constants
MAX_CONVERSATION_LENGTH = 50
MAX_QUESTION_LENGTH = 500

# Language configurations
LANGUAGES = {
    "English": {"code": "en", "greeting": "Share your crossroad...", "button": "Seek Guidance", "thinking": "Contemplating your path..."},
    "Hindi - हिंदी": {"code": "hi", "greeting": "अपना प्रश्न साझा करें...", "button": "मार्गदर्शन लें", "thinking": "आपके मार्ग पर विचार हो रहा है..."},
    "Telugu - తెలుగు": {"code": "te", "greeting": "మీ ప్రశ్నను పంచుకోండి...", "button": "మార్గదర్శనం పొందండి", "thinking": "మీ మార్గంపై ఆలోచిస్తున్నారు..."},
    "Tamil - தமிழ்": {"code": "ta", "greeting": "உங்கள் கேள்வியை பகிரவும்...", "button": "வழிகாட்டுதல் பெறுங்கள்", "thinking": "உங்கள் பாதையை சிந்திக்கிறார்..."},
    "Sanskrit - संस्कृत": {"code": "sa", "greeting": "स्व प्रश्नं वद...", "button": "मार्गदर्शनं प्राप्नुहि", "thinking": "तव मार्गं चिन्तयति..."},
}


def inject_devotional_css():
    """Inject warm devotional themed CSS with background image"""
    bg_image = get_base64_image("assets/bg_krishna.png")

    bg_style = ""
    if bg_image:
        bg_style = f"""
        .stApp {{
            background-image:
                linear-gradient(to bottom,
                    rgba(10, 5, 2, 0.85) 0%,
                    rgba(20, 10, 5, 0.75) 30%,
                    rgba(15, 8, 20, 0.8) 60%,
                    rgba(10, 5, 2, 0.9) 100%),
                url("{bg_image}");
            background-size: cover;
            background-position: center top;
            background-attachment: fixed;
            background-repeat: no-repeat;
            min-height: 100vh;
        }}
        """
    else:
        bg_style = """
        .stApp {
            background: linear-gradient(165deg,
                #1a0a05 0%,
                #2d1810 15%,
                #1a1025 35%,
                #0d1a2d 55%,
                #1a1025 75%,
                #2d1810 90%,
                #1a0a05 100%);
            min-height: 100vh;
        }
        """

    css_rest = """
    /* Subtle sacred geometry pattern */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image:
            radial-gradient(circle at 20% 30%, rgba(255, 153, 51, 0.03) 0%, transparent 40%),
            radial-gradient(circle at 80% 70%, rgba(255, 215, 0, 0.03) 0%, transparent 40%),
            radial-gradient(circle at 50% 50%, rgba(255, 140, 0, 0.02) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }

    .main .block-container {
        position: relative;
        z-index: 1;
        padding-top: 1rem;
        max-width: 850px;
    }

    /* Title styling - diverging paths theme */
    .title-container {
        text-align: center;
        margin: 1rem 0 0.5rem 0;
        font-family: 'Cormorant Garamond', serif;
        font-weight: 700;
        font-size: 3.5rem;
        letter-spacing: 4px;
    }

    .title-cross {
        color: #d4a853;
        text-shadow: 0 2px 15px rgba(212, 168, 83, 0.4);
        display: inline-block;
        transform: skewX(-3deg);
    }

    .title-divider {
        color: #ff9933;
        font-size: 4.5rem;
        font-weight: 300;
        margin: 0 0.1rem;
        text-shadow:
            0 0 10px rgba(255, 153, 51, 0.8),
            0 0 30px rgba(255, 140, 0, 0.6),
            0 0 50px rgba(212, 168, 83, 0.4);
        display: inline-block;
        transform: scaleY(1.3);
        vertical-align: middle;
    }

    .title-roads {
        color: #ff6b35;
        text-shadow: 0 2px 15px rgba(255, 107, 53, 0.5);
        display: inline-block;
        transform: skewX(3deg);
    }

    h1 {
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 600 !important;
        font-size: 3.2rem !important;
        letter-spacing: 8px;
        text-align: center;
        color: #d4a853 !important;
        text-shadow: 0 2px 20px rgba(212, 168, 83, 0.3);
        margin-bottom: 0 !important;
    }

    .tagline {
        text-align: center;
        font-family: 'Lora', serif;
        font-style: italic;
        font-size: 1.1rem;
        color: #b89d6a;
        letter-spacing: 2px;
        margin-top: 0.5rem;
        opacity: 0.9;
    }

    h2, h3 {
        font-family: 'Cormorant Garamond', serif !important;
        color: #d4a853 !important;
        font-weight: 600 !important;
        letter-spacing: 1px;
    }

    /* Hero image container */
    .hero-container {
        text-align: center;
        margin: 2rem auto;
        position: relative;
    }

    .hero-image {
        width: 100%;
        max-width: 700px;
        height: auto;
        border-radius: 8px;
        box-shadow:
            0 10px 40px rgba(0, 0, 0, 0.5),
            0 0 60px rgba(212, 168, 83, 0.1);
        border: 1px solid rgba(212, 168, 83, 0.2);
    }

    /* Circular Krishna image */
    .krishna-circle {
        width: 180px;
        height: 180px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #d4a853;
        box-shadow:
            0 0 30px rgba(212, 168, 83, 0.4),
            0 0 60px rgba(255, 140, 0, 0.2);
        margin: 1.5rem auto;
        display: block;
    }

    /* Welcome section */
    .welcome-section {
        text-align: center;
        max-width: 650px;
        margin: 2rem auto;
        padding: 2rem;
        background: linear-gradient(135deg, rgba(45, 24, 16, 0.6) 0%, rgba(26, 16, 37, 0.6) 100%);
        border-radius: 8px;
        border: 1px solid rgba(212, 168, 83, 0.15);
    }

    .welcome-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.6rem;
        font-weight: 600;
        color: #d4a853;
        margin-bottom: 1rem;
        letter-spacing: 1px;
    }

    .welcome-text {
        font-family: 'Lora', serif;
        font-size: 1.05rem;
        color: #c4b896;
        line-height: 1.8;
        font-weight: 400;
    }

    .welcome-quote {
        font-family: 'Lora', serif;
        font-style: italic;
        font-size: 0.95rem;
        color: #a89860;
        margin-top: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(212, 168, 83, 0.2);
    }

    /* Query counter */
    .counter-section {
        text-align: center;
        margin: 1.5rem auto;
        padding: 1rem;
    }

    .counter-number {
        font-family: 'Inter', sans-serif;
        font-size: 4rem;
        font-weight: 300;
        color: #ff6b35;
        text-shadow: 0 0 30px rgba(255, 107, 53, 0.4);
        display: block;
        letter-spacing: 4px;
    }

    .counter-label {
        font-family: 'Lora', serif;
        font-size: 0.9rem;
        color: #b89d6a;
        font-style: italic;
        letter-spacing: 1px;
    }

    /* Crossroads visual */
    .crossroads-visual {
        text-align: center;
        margin: 1.5rem 0;
        font-size: 2rem;
        color: #d4a853;
        opacity: 0.6;
        letter-spacing: 20px;
    }

    /* Text styling */
    .stMarkdown, .stMarkdown p {
        color: #d4c4a8 !important;
        font-family: 'Lora', serif;
        font-size: 1rem;
        line-height: 1.7;
    }

    /* Form styling */
    .stForm {
        background: linear-gradient(135deg, rgba(45, 24, 16, 0.7) 0%, rgba(26, 16, 37, 0.7) 100%) !important;
        border: 1px solid rgba(212, 168, 83, 0.2);
        border-radius: 8px;
        padding: 1.5rem;
    }

    /* Input field */
    .stTextInput > div > div > input {
        background: rgba(10, 5, 15, 0.8) !important;
        border: 1px solid rgba(212, 168, 83, 0.3) !important;
        border-radius: 6px !important;
        color: #e8dcc8 !important;
        font-family: 'Lora', serif !important;
        font-size: 1.05rem !important;
        padding: 0.85rem 1rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #d4a853 !important;
        box-shadow: 0 0 20px rgba(212, 168, 83, 0.2) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #8a7a5a !important;
        font-style: italic;
    }

    .stTextInput > label {
        color: #b89d6a !important;
        font-family: 'Cormorant Garamond', serif !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        letter-spacing: 1px;
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #d4a853 0%, #b8860b 50%, #d4a853 100%) !important;
        background-size: 200% auto !important;
        color: #1a0a05 !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.8rem 2.5rem !important;
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        letter-spacing: 2px;
        transition: all 0.4s ease !important;
        box-shadow: 0 4px 20px rgba(212, 168, 83, 0.3);
    }

    .stButton > button:hover {
        background-position: right center !important;
        box-shadow: 0 6px 30px rgba(212, 168, 83, 0.5) !important;
        transform: translateY(-2px);
    }

    /* Question box */
    .question-box {
        background: linear-gradient(135deg, rgba(212, 168, 83, 0.08) 0%, rgba(45, 24, 16, 0.4) 100%);
        border-left: 3px solid #d4a853;
        border-radius: 0 6px 6px 0;
        padding: 1.2rem 1.5rem;
        margin: 1.5rem 0 0.5rem 0;
    }

    .question-label {
        color: #d4a853;
        font-family: 'Cormorant Garamond', serif;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.5rem;
    }

    .question-text {
        color: #e8dcc8;
        font-family: 'Lora', serif;
        font-size: 1.05rem;
    }

    /* Answer box */
    .answer-box {
        background: linear-gradient(135deg, rgba(26, 16, 37, 0.5) 0%, rgba(13, 26, 45, 0.5) 100%);
        border-left: 3px solid #7b68a6;
        border-radius: 0 6px 6px 0;
        padding: 1.2rem 1.5rem;
        margin: 0.5rem 0 1rem 1.5rem;
    }

    .answer-label {
        color: #a89dc8;
        font-family: 'Cormorant Garamond', serif;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.5rem;
    }

    .answer-text {
        color: #d4c8e8;
        font-family: 'Lora', serif;
        font-size: 1.02rem;
        line-height: 1.7;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(45, 24, 16, 0.5) !important;
        border: 1px solid rgba(212, 168, 83, 0.15) !important;
        border-radius: 6px !important;
        color: #b89d6a !important;
        font-family: 'Lora', serif !important;
    }

    .streamlit-expanderContent {
        background: rgba(26, 10, 5, 0.6) !important;
        border: 1px solid rgba(212, 168, 83, 0.1);
        border-top: none;
        border-radius: 0 0 6px 6px;
        color: #c4b896 !important;
        font-family: 'Lora', serif !important;
    }

    /* Select box */
    .stSelectbox > div > div {
        background: rgba(10, 5, 15, 0.8) !important;
        border: 1px solid rgba(212, 168, 83, 0.3) !important;
        border-radius: 6px !important;
    }

    .stSelectbox > label {
        color: #b89d6a !important;
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 600 !important;
    }

    /* Divider */
    .sacred-divider {
        text-align: center;
        margin: 2rem 0;
        color: #d4a853;
        opacity: 0.4;
        font-size: 1.2rem;
        letter-spacing: 15px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a0a05 0%, #2d1810 50%, #1a1025 100%) !important;
        border-right: 1px solid rgba(212, 168, 83, 0.1);
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: #b89d6a !important;
    }

    /* Metrics */
    .metric-box {
        background: rgba(45, 24, 16, 0.5);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 6px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    .metric-label {
        color: #8a7a5a;
        font-family: 'Lora', serif;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .metric-value {
        color: #d4a853;
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.4rem;
        font-weight: 700;
    }

    /* Voice button */
    .mic-container {
        text-align: center;
        margin: 1rem 0;
    }

    .mic-button {
        background: linear-gradient(135deg, #d4a853, #b8860b);
        border: none;
        border-radius: 50%;
        width: 56px;
        height: 56px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 20px rgba(212, 168, 83, 0.3);
        transition: all 0.3s ease;
    }

    .mic-button:hover {
        transform: scale(1.08);
        box-shadow: 0 6px 30px rgba(212, 168, 83, 0.5);
    }

    .mic-button svg {
        width: 24px;
        height: 24px;
        fill: #1a0a05;
    }

    .mic-label {
        color: #8a7a5a;
        font-family: 'Lora', serif;
        font-size: 0.85rem;
        margin-top: 0.5rem;
        font-style: italic;
    }

    /* Hide streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Info/warning boxes */
    .stAlert {
        background: rgba(45, 24, 16, 0.6) !important;
        border: 1px solid rgba(212, 168, 83, 0.2) !important;
        color: #d4a853 !important;
        font-family: 'Lora', serif !important;
    }

    /* Speak button */
    .speak-btn {
        background: transparent;
        border: 1px solid rgba(212, 168, 83, 0.3);
        border-radius: 4px;
        color: #b89d6a;
        padding: 0.3rem 0.8rem;
        font-family: 'Lora', serif;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .speak-btn:hover {
        background: rgba(212, 168, 83, 0.1);
        border-color: #d4a853;
    }

    /* Mobile Responsive Styles */
    @media (max-width: 768px) {
        .title-container {
            font-size: 2.2rem;
            letter-spacing: 2px;
        }

        .title-divider {
            font-size: 3rem;
        }

        .main .block-container {
            padding: 0.5rem 1rem;
        }

        .welcome-section {
            padding: 1.25rem;
            margin: 1rem auto;
        }

        .welcome-title {
            font-size: 1.3rem;
        }

        .welcome-text {
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .welcome-quote {
            font-size: 0.85rem;
        }

        .counter-number {
            font-size: 3rem;
        }

        .counter-label {
            font-size: 0.8rem;
        }

        .tagline {
            font-size: 0.9rem;
            letter-spacing: 1px;
        }

        .stTextInput > div > div > input {
            font-size: 1rem !important;
            padding: 0.75rem !important;
        }

        .stButton > button {
            width: 100% !important;
            padding: 0.75rem 1.5rem !important;
            font-size: 1rem !important;
        }

        .mic-button {
            width: 50px;
            height: 50px;
        }

        .mic-label {
            font-size: 0.75rem;
        }

        .question-box, .answer-box {
            padding: 1rem;
            margin: 1rem 0;
        }

        .answer-box {
            margin-left: 0.5rem;
        }

        .question-text, .answer-text {
            font-size: 0.95rem;
        }

        h2, h3 {
            font-size: 1.3rem !important;
        }

        .hero-image {
            max-width: 100%;
        }

        .sacred-divider {
            margin: 1.5rem 0;
            letter-spacing: 10px;
        }
    }

    @media (max-width: 480px) {
        .title-container {
            font-size: 1.8rem;
            letter-spacing: 1px;
        }

        .title-divider {
            font-size: 2.5rem;
            margin: 0;
        }

        .title-cross, .title-roads {
            transform: none;
        }

        .welcome-section {
            padding: 1rem;
        }

        .welcome-title {
            font-size: 1.1rem;
        }

        .welcome-text {
            font-size: 0.9rem;
        }

        .counter-number {
            font-size: 2.2rem;
        }

        .counter-label {
            font-size: 0.7rem;
        }

        .tagline {
            font-size: 0.8rem;
        }

        .stForm {
            padding: 1rem;
        }
    }
    """

    # Combine all CSS parts
    font_import = """
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;1,400&display=swap');
    """

    full_css = f"<style>{font_import}{bg_style}{css_rest}</style>"
    st.markdown(full_css, unsafe_allow_html=True)


def inject_voice_script():
    """Inject JavaScript for speech recognition"""
    st.markdown("""
    <script>
    const voiceState = window.crossroadsVoiceState || {
        recognition: null,
        isListening: false,
        micClickBound: false
    };
    window.crossroadsVoiceState = voiceState;

    function initSpeechRecognition() {
        if (voiceState.recognition) {
            return;
        }
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            voiceState.recognition = new SpeechRecognition();
            voiceState.recognition.continuous = false;
            voiceState.recognition.interimResults = false;

            voiceState.recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                const inputField = document.querySelector('input[data-testid="stTextInput"]') ||
                                   document.querySelector('.stTextInput input');
                if (inputField) {
                    inputField.value = transcript;
                    inputField.dispatchEvent(new Event('input', { bubbles: true }));
                }
                stopListening();
            };

            voiceState.recognition.onerror = function(event) {
                stopListening();
            };

            voiceState.recognition.onend = function() {
                stopListening();
            };
        }
    }

    function bindMicButton() {
        if (voiceState.micClickBound) {
            return;
        }

        document.addEventListener('click', function(event) {
            const micButton = event.target.closest('#micButton');
            if (!micButton) {
                return;
            }

            event.preventDefault();
            toggleListening(micButton.dataset.langCode || 'en-US');
        });

        voiceState.micClickBound = true;
    }

    function startListening(langCode) {
        if (!voiceState.recognition) initSpeechRecognition();
        if (voiceState.recognition && !voiceState.isListening) {
            voiceState.recognition.lang = langCode || 'en-US';
            voiceState.isListening = true;
            const btn = document.getElementById('micButton');
            if (btn) {
                btn.style.background = 'linear-gradient(135deg, #c94a4a, #8b0000)';
            }
            voiceState.recognition.start();
        }
    }

    function stopListening() {
        voiceState.isListening = false;
        const btn = document.getElementById('micButton');
        if (btn) {
            btn.style.background = 'linear-gradient(135deg, #d4a853, #b8860b)';
        }
        if (voiceState.recognition) {
            try { voiceState.recognition.stop(); } catch(e) {}
        }
    }

    function toggleListening(langCode) {
        if (voiceState.isListening) {
            stopListening();
        } else {
            startListening(langCode);
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        initSpeechRecognition();
        bindMicButton();
    });
    if (document.readyState !== 'loading') {
        initSpeechRecognition();
        bindMicButton();
    }
    </script>
    """, unsafe_allow_html=True)


def display_hero_section():
    """Display the hero image - Krishna and Arjuna at the crossroads"""
    try:
        st.image("krishna_arjuna.png", use_container_width=True)
    except Exception:
        pass


def display_krishna_circle():
    """Display circular Krishna image"""
    st.markdown("""
    <img src="https://i.pinimg.com/originals/30/7b/c8/307bc8a52ef36c5fb7d6b61d3d876bb0.jpg"
         alt="Sri Krishna"
         class="krishna-circle"
         onerror="this.src='https://upload.wikimedia.org/wikipedia/commons/e/e1/Krishna_with_flute.jpg'"/>
    """, unsafe_allow_html=True)


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
    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = "English"


@cache_response
def process_question(question, gita_processor, response_generator, context,
                     conversation, language="English"):
    """Process user question with caching and validation"""
    try:
        if not question.strip() or len(question) > MAX_QUESTION_LENGTH:
            raise ValueError("Invalid question length")

        relevant_verses = gita_processor.find_relevant_verses(question)
        response = response_generator.generate_response(
            question, relevant_verses, context, conversation, language)

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


def display_conversation_history(lang_config):
    """Display conversation history"""
    if st.session_state.conversation:
        st.markdown("### Your Journey")
        displayed_questions = set()

        for conv in st.session_state.conversation:
            if conv["question"] in displayed_questions:
                continue
            displayed_questions.add(conv["question"])

            st.markdown(f"""
                <div class="question-box">
                    <div class="question-label">Your Crossroad</div>
                    <div class="question-text">{conv["question"]}</div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="answer-box">
                    <div class="answer-label">Guidance from the Gita</div>
                    <div class="answer-text">{conv["short_answer"]}</div>
                </div>
            """, unsafe_allow_html=True)

            with st.expander("Read detailed explanation with verses"):
                st.markdown(conv["detailed_explanation"])

            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("Listen", key=f"speak_{conv.get('id', 0)}"):
                    st.markdown(f"""
                        <script>
                        if ('speechSynthesis' in window) {{
                            window.speechSynthesis.cancel();
                            const utterance = new SpeechSynthesisUtterance(`{conv["short_answer"].replace('`', '').replace('"', "'")}`);
                            utterance.lang = '{lang_config["code"]}';
                            utterance.rate = 0.9;
                            window.speechSynthesis.speak(utterance);
                        }}
                        </script>
                    """, unsafe_allow_html=True)

            st.markdown('<div class="sacred-divider">* * *</div>', unsafe_allow_html=True)


def handle_user_input(user_question, session_id, gita_processor,
                      response_generator, language):
    """Handle user input with error handling"""
    try:
        if 'last_processed_question' in st.session_state and \
           st.session_state.last_processed_question == user_question:
            return

        if not rate_limiter.is_allowed(session_id):
            st.warning("Please pause for a moment before seeking more guidance.")
            return

        st.session_state.processing = True
        start_time = time.time()

        if len(st.session_state.conversation) >= MAX_CONVERSATION_LENGTH:
            st.session_state.conversation.pop(0)

        try:
            response_data = process_question(user_question, gita_processor,
                                           response_generator,
                                           st.session_state.context,
                                           st.session_state.conversation,
                                           language)
            monitor.log_response_metrics(session_id,
                                       time.time() - start_time, True)

            st.session_state.last_processed_question = user_question
            st.session_state.conversation.append({
                "question": user_question,
                "short_answer": response_data["short_answer"],
                "detailed_explanation": response_data["detailed_explanation"],
                "id": len(st.session_state.conversation)
            })
            # Increment the global query counter
            increment_query_count()
        except Exception as e:
            monitor.log_response_metrics(session_id,
                                       time.time() - start_time, False,
                                       str(e))

        response_time = time.time() - start_time
        monitor.log_performance_metric("total_response_time", response_time, {
            "question_length": len(user_question),
            "session_id": session_id
        })

        st.session_state.question_processed = True

    except Exception as e:
        st.error("Unable to provide guidance at this moment. Please try again.")
        monitor.log_error(session_id, e, {"context": "handle_user_input"})
    finally:
        st.session_state.processing = False


def display_sidebar():
    """Display sidebar with info and metrics"""
    st.sidebar.markdown("### About CrossRoads")
    st.sidebar.markdown("""
    <div style="color: #b89d6a; font-family: 'Lora', serif; font-size: 0.9rem; line-height: 1.6;">
        Every soul faces crossroads - moments where paths diverge and choices define destiny.
        <br/><br/>
        CrossRoads brings ancient wisdom from the Bhagavad Gita to illuminate your modern dilemmas,
        guided by the eternal principles of Dharma.
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")

    metrics = monitor.get_metrics()

    metric_items = [
        ('Seekers Guided', metrics.get('total_interactions', 0)),
        ('Paths Illuminated', metrics.get('successful_responses', 0)),
    ]

    for label, value in metric_items:
        st.sidebar.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value:,}</div>
            </div>
        """, unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="CrossRoads - Dharma-Guided Decisions",
        page_icon="",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    try:
        initialize_session_state()
        session_id = init_session()

        inject_devotional_css()
        inject_voice_script()

        gita_processor = GitaProcessor()
        response_generator = ResponseGenerator()

        # Title - stylized with diverging paths theme
        st.markdown("""
        <div class="title-container">
            <span class="title-cross">CROSS</span><span class="title-divider">|</span><span class="title-roads">ROADS</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<p class="tagline">Where Ancient Wisdom Meets Modern Decisions</p>', unsafe_allow_html=True)

        # Hero image
        display_hero_section()

        # Welcome section
        st.markdown("""
        <div class="welcome-section">
            <div class="welcome-title">Standing at a Crossroad?</div>
            <div class="welcome-text">
                Life presents us with countless crossroads - startup versus stability,
                family versus ambition, passion versus pragmatism. These moments of choice
                shape who we become.
                <br/><br/>
                Drawing from the timeless wisdom of the Bhagavad Gita, CrossRoads helps you
                navigate life's difficult decisions through the lens of Dharma - your sacred duty
                aligned with your true nature.
            </div>
            <div class="welcome-quote">
                "Karmanye vadhikaraste ma phaleshu kadachana"<br/>
                You have the right to work, but never to its fruits.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Display query counter with counting animation
        query_count = get_query_count()
        st.markdown(f"""
        <div class="counter-section">
            <span class="counter-number" id="queryCounter" data-target="{query_count}">0</span>
            <span class="counter-label">life decisions made easier</span>
        </div>
        <script>
        (function() {{
            const counter = document.getElementById('queryCounter');
            if (!counter || counter.dataset.animated === 'true') return;

            const target = parseInt(counter.dataset.target);
            const duration = 2000;
            const startValue = Math.max(0, target - 500);
            const increment = (target - startValue) / (duration / 16);
            let current = startValue;

            counter.dataset.animated = 'true';

            function updateCounter() {{
                current += increment;
                if (current < target) {{
                    counter.textContent = Math.floor(current).toLocaleString();
                    requestAnimationFrame(updateCounter);
                }} else {{
                    counter.textContent = target.toLocaleString();
                }}
            }}

            setTimeout(updateCounter, 500);
        }})();
        </script>
        """, unsafe_allow_html=True)

        # Language selector
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            selected_lang = st.selectbox(
                "Choose Your Language",
                options=list(LANGUAGES.keys()),
                index=list(LANGUAGES.keys()).index(st.session_state.selected_language),
                key="lang_select"
            )
            st.session_state.selected_language = selected_lang

        lang_config = LANGUAGES[selected_lang]

        # Voice input
        lang_code_map = {"English": "en-US", "Hindi - हिंदी": "hi-IN", "Telugu - తెలుగు": "te-IN", "Tamil - தமிழ்": "ta-IN", "Sanskrit - संस्कृत": "sa-IN"}
        current_lang_code = lang_code_map.get(selected_lang, "en-US")

        st.markdown(f"""
        <div class="mic-container">
            <button id="micButton" class="mic-button" data-lang-code="{current_lang_code}">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z"/>
                </svg>
            </button>
            <div class="mic-label">Tap to speak your question</div>
        </div>
        """, unsafe_allow_html=True)

        # Input form
        with st.form(key='question_form', clear_on_submit=True):
            user_question = st.text_input(
                lang_config["greeting"],
                key="user_input",
                disabled=st.session_state.processing,
                max_chars=MAX_QUESTION_LENGTH,
                placeholder="Should I leave my job for a startup? How do I balance career and family?..."
            )
            submit_button = st.form_submit_button(lang_config['button'])

        if st.session_state.processing:
            with st.spinner(lang_config['thinking']):
                st.markdown("""
                <div style="text-align: center; padding: 2rem;">
                    <div style="color: #d4a853; font-family: 'Cormorant Garamond', serif; font-size: 1.2rem;">
                        Seeking wisdom from the Gita...
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if submit_button and user_question:
            with st.spinner("Seeking wisdom from the Gita..."):
                handle_user_input(user_question, session_id, gita_processor,
                                 response_generator, selected_lang)

            if st.session_state.question_processed:
                st.session_state.question_processed = False
                st.rerun()

        # Conversation history
        display_conversation_history(lang_config)

        # Sidebar
        display_sidebar()

    except Exception as e:
        monitor.log_error("system", e, {"context": "main_function"})
        st.error("The path is temporarily unclear. Please try again.")


if __name__ == "__main__":
    main()
