import streamlit as st
import os
import wave
import tempfile
from google import genai
from google.genai import types
import io
import base64
import hashlib

# Page configuration
st.set_page_config(
    page_title="AI-udio",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication functions
def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_authentication():
    """Check if user is authenticated"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    return st.session_state.authenticated

def login_page():
    """Display login page"""
    st.markdown('<div class="main-header"><h1>🔐 AI-udio Login</h1><p>Please sign in to access the application</p></div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Sign In")
        
        if submit_button:
            # Check credentials against secrets
            if (username == st.secrets["username"] and 
                password == st.secrets["password"]):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
    
    st.markdown("---")
    st.info("💡 Contact your administrator for login credentials")

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    st.session_state.username = None
    if 'messages' in st.session_state:
        del st.session_state.messages
    if 'audio_files' in st.session_state:
        del st.session_state.audio_files
    st.rerun()

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background-color: #f9f9f9;
        margin-bottom: 1rem;
    }
    .user-message {
        text-align: right;
        background-color: #007bff;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        display: inline-block;
        max-width: 80%;
        float: right;
        clear: both;
    }
    .ai-message {
        text-align: left;
        background-color: #e9ecef;
        color: #333;
        padding: 0.5rem 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        display: inline-block;
        max-width: 80%;
        float: left;
        clear: both;
    }
    .clearfix::after {
        content: "";
        display: table;
        clear: both;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'audio_files' not in st.session_state:
    st.session_state.audio_files = []

# Check authentication first
if not check_authentication():
    login_page()
    st.stop()

# Set up Google API key from secrets
os.environ['GOOGLE_API_KEY'] = st.secrets["google_api_key"]

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM data to a wave file"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def generate_speech(text, model_name="gemini-2.5-flash-preview-tts", voice_name="Fenrir"):
    """Generate speech from text using Gemini TTS"""
    try:
        client = genai.Client()
        
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            )
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            wave_file(tmp_file.name, audio_data)
            return tmp_file.name
            
    except Exception as e:
        st.error(f"Error generating speech: {str(e)}")
        return None

def generate_ai_response(user_input):
    """Generate AI response using Gemini (text-only for conversation)"""
    try:
        client = genai.Client()
        
        # Build conversation context
        conversation_context = "You are a helpful AI assistant having a friendly conversation. "
        conversation_context += "Keep responses conversational and engaging. "
        
        # Add recent conversation history for context
        if st.session_state.messages:
            conversation_context += "Previous conversation:\n"
            for msg in st.session_state.messages[-6:]:  # Last 6 messages for context
                conversation_context += f"{msg['role']}: {msg['content']}\n"
        
        conversation_context += f"User: {user_input}\nAssistant:"
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=conversation_context,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
            )
        )
        
        return response.text
        
    except Exception as e:
        st.error(f"Error generating AI response: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request."

def get_audio_player_html(audio_file_path):
    """Generate HTML audio player"""
    with open(audio_file_path, 'rb') as audio_file:
        audio_bytes = audio_file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
    audio_html = f"""
    <audio controls style="width: 100%; margin-top: 10px;">
        <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
        Your browser does not support the audio element.
    </audio>
    """
    return audio_html

# Main UI
st.markdown('<div class="main-header"><h1>🎙️ AI-udio</h1><p>Conversational Text-to-Speech AI</p></div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Settings")
    
    # User info and logout
    st.success(f"👋 Welcome, {st.session_state.username}!")
    if st.button("🚪 Logout"):
        logout()
    
    st.markdown("---")
    
    # Model selection
    tts_model = st.selectbox(
        "TTS Model",
        ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"],
        help="Choose the TTS model"
    )
    
    # Voice selection
    voice_name = st.selectbox(
        "Voice",
        ["Fenrir"],
        help="Fenrir is excitable and energetic"
    )
    
    # Language info
    st.info("📢 Supported Languages:\n- English (US)\n- Indonesian (Indonesia)")
    
    # Clear conversation
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.session_state.audio_files = []
        st.rerun()

# Main chat interface
col1, col2 = st.columns([2, 1])

with col1:
    st.header("💬 Conversation")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for i, message in enumerate(st.session_state.messages):
            if message["role"] == "user":
                st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ai-message">{message["content"]}</div>', unsafe_allow_html=True)
                # Add audio player if available
                if i < len(st.session_state.audio_files) and st.session_state.audio_files[i]:
                    audio_html = get_audio_player_html(st.session_state.audio_files[i])
                    st.markdown(audio_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.header("🎵 Audio Controls")
    
    # Quick TTS without conversation
    st.subheader("Direct TTS")
    quick_text = st.text_area("Enter text for TTS", placeholder="Type something to convert to speech...")
    
    if st.button("🎵 Generate Speech", key="quick_tts"):
        if quick_text:
            with st.spinner("Generating speech..."):
                audio_file = generate_speech(quick_text, tts_model, voice_name)
                if audio_file:
                    st.success("✅ Speech generated!")
                    audio_html = get_audio_player_html(audio_file)
                    st.markdown(audio_html, unsafe_allow_html=True)
        else:
            st.error("Please enter some text")

# Chat input
st.header("💭 Chat with AI")
user_input = st.text_input("Type your message...", placeholder="Say something to start the conversation!")

if st.button("Send & Speak", key="send_message") or user_input:
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.spinner("AI is thinking..."):
            # Generate AI response
            ai_response = generate_ai_response(user_input)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
            # Generate speech for AI response
            audio_file = generate_speech(ai_response, tts_model, voice_name)
            st.session_state.audio_files.append(audio_file)
            
        st.rerun()
    elif not user_input:
        st.error("Please enter a message")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🎙️ AI-udio - Powered by Google Gemini TTS & Conversational AI</p>
    <p>Using Fenrir voice for an excitable and energetic experience!</p>
</div>
""", unsafe_allow_html=True)

# Instructions
with st.expander("📖 How to Use"):
    st.markdown("""
    1. **Sign In**: Use your provided credentials to access the app
    2. **Choose Settings**: Select your preferred TTS model and voice in the sidebar
    3. **Start Chatting**: Type a message and click 'Send & Speak' for conversation with voice
    4. **Direct TTS**: Use the right panel for quick text-to-speech without conversation
    5. **Logout**: Click the logout button in the sidebar when done
    
    **Features:**
    - 🔐 Secure authentication system
    - 🤖 Conversational AI with Gemini
    - 🎵 Text-to-speech with Fenrir voice
    - 🌐 Supports English and Indonesian
    - 💾 Conversation history
    - 🎚️ Adjustable settings
    """)