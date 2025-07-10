import streamlit as st
import wave
import io
import base64
from google import genai
from google.genai import types
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder
import tempfile
import os
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="AI-udio: Voice-to-Voice Chat",
    page_icon="🎙️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.2em;
        margin-bottom: 2em;
    }
    .chat-message {
        padding: 1em;
        margin: 0.5em 0;
        border-radius: 10px;
        max-width: 80%;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: auto;
        text-align: right;
    }
    .ai-message {
        background-color: #f5f5f5;
        margin-right: auto;
    }
    .voice-controls {
        background-color: #f0f2f6;
        padding: 2em;
        border-radius: 10px;
        margin: 2em 0;
        text-align: center;
    }
    .record-button {
        background-color: #ff4444;
        color: white;
        border: none;
        border-radius: 50%;
        width: 100px;
        height: 100px;
        font-size: 2em;
        cursor: pointer;
        margin: 1em;
    }
    .record-button:hover {
        background-color: #ff6666;
    }
    .status-indicator {
        padding: 0.5em;
        border-radius: 5px;
        margin: 1em 0;
        text-align: center;
        font-weight: bold;
    }
    .listening {
        background-color: #ffe6e6;
        color: #cc0000;
    }
    .processing {
        background-color: #fff3cd;
        color: #856404;
    }
    .ready {
        background-color: #d4edda;
        color: #155724;
    }
    .login-container {
        max-width: 400px;
        margin: 2em auto;
        padding: 2em;
        border: 1px solid #ddd;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.get("authenticated", False)

def authenticate_user(username, password):
    """Authenticate user against Streamlit secrets"""
    try:
        correct_username = st.secrets["auth"]["username"]
        correct_password = st.secrets["auth"]["password"]
        return username == correct_username and password == correct_password
    except KeyError:
        st.error("Authentication secrets not configured properly")
        return False

def login_page():
    """Display login page"""
    st.markdown('<h1 class="main-header">🎙️ AI-udio Login</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Voice-to-Voice AI Conversation System</p>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("### 🔐 Please Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login", type="primary")
            
            if login_button:
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.success("Login successful! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        st.markdown('</div>', unsafe_allow_html=True)

def wave_file_from_bytes(pcm_data, channels=1, rate=24000, sample_width=2):
    """Convert PCM data to wave file bytes"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    buffer.seek(0)
    return buffer.getvalue()

def create_audio_player(audio_data, key=None, autoplay=True):
    """Create an HTML audio player for the given audio data"""
    audio_base64 = base64.b64encode(audio_data).decode()
    autoplay_attr = "autoplay" if autoplay else ""
    audio_html = f"""
    <audio controls {autoplay_attr} style="width: 100%;">
        <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
        Your browser does not support the audio element.
    </audio>
    """
    return audio_html

def process_audio_bytes(audio_bytes):
    """Process audio bytes and return speech recognition audio object"""
    if audio_bytes is None:
        return None
    
    try:
        # Save audio bytes to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        # Load audio file with speech recognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_file_path) as source:
            audio = recognizer.record(source)
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        return audio
    except Exception as e:
        st.error(f"Error processing audio: {str(e)}")
        return None

def transcribe_audio(audio_data):
    """Transcribe audio to text using Google Speech Recognition"""
    recognizer = sr.Recognizer()
    
    try:
        # Transcribe audio
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        st.error("Could not understand audio. Please speak clearly.")
        return None
    except sr.RequestError as e:
        st.error(f"Error with speech recognition service: {str(e)}")
        return None

def get_ai_response_with_audio(user_input, model_choice, api_key):
    """Generate AI response with audio using Gemini TTS"""
    try:
        # Initialize the client
        client = genai.Client(api_key=api_key)
        
        # Generate response with audio
        response = client.models.generate_content(
            model=model_choice,
            contents=user_input,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name='Fenrir',  # Using the excitable voice
                        )
                    )
                ),
            )
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        
        # Get text response (if available)
        text_response = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                text_response += part.text
        
        # If no text response, use a default message
        if not text_response:
            text_response = "AI response generated with audio"
        
        return text_response, audio_data
        
    except Exception as e:
        st.error(f"Error generating AI response: {str(e)}")
        return None, None

def main_app():
    """Main application after authentication"""
    # Header
    st.markdown('<h1 class="main-header">🎙️ AI-udio</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Voice-to-Voice AI Conversation System</p>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Get API key from secrets
        try:
            api_key = st.secrets["google_api_key"]
            st.success("✅ API Key loaded from secrets")
        except KeyError:
            st.error("❌ Google API Key not found in secrets")
            st.stop()
        
        # Model selection
        model_choice = st.selectbox(
            "Select TTS Model",
            ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"],
            help="Choose between Flash (faster) or Pro (higher quality) TTS models"
        )
        
        # Voice info
        st.markdown("""
        **🎤 Voice:** Fenrir (Excitable)  
        **🌍 Languages:** Auto-detected  
        **📊 Features:** Full voice-to-voice conversation  
        **🔊 Audio:** Input & Output enabled
        """)
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
        
        # Logout button
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.clear()
            st.rerun()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "recording_status" not in st.session_state:
        st.session_state.recording_status = "ready"
    
    # Voice Controls Section
    st.markdown("---")
    st.markdown("### 🎙️ Voice Controls")
    
    # Status indicator
    status_class = st.session_state.recording_status
    status_messages = {
        "ready": "🟢 Ready to record",
        "listening": "🔴 Listening...",
        "processing": "🟡 Processing audio...",
        "responding": "🔵 AI is responding..."
    }
    
    st.markdown(f"""
    <div class="status-indicator {status_class}">
        {status_messages.get(status_class, "Ready")}
    </div>
    """, unsafe_allow_html=True)
    
    # Audio recorder widget
    st.markdown("#### 🎤 Click to Record Your Voice")
    audio_bytes = audio_recorder(
        text="Click to record",
        recording_color="#ff0000",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="2x",
        pause_threshold=2.0,
        sample_rate=16000,
        key="audio_recorder"
    )
    
    # Process recorded audio
    if audio_bytes:
        st.session_state.recording_status = "processing"
        
        # Display audio player for user's recording
        st.markdown("#### 🎧 Your Recording:")
        st.audio(audio_bytes, format="audio/wav")
        
        # Process audio and get transcription
        with st.spinner("🔄 Converting speech to text..."):
            audio_data = process_audio_bytes(audio_bytes)
            
            if audio_data:
                transcribed_text = transcribe_audio(audio_data)
                
                if transcribed_text:
                    st.success(f"📝 Transcribed: \"{transcribed_text}\"")
                    
                    # Add user message
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": transcribed_text,
                        "audio": audio_bytes,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    # Get AI response with voice
                    st.session_state.recording_status = "responding"
                    with st.spinner("🤖 AI is generating voice response..."):
                        ai_response, ai_audio_data = get_ai_response_with_audio(transcribed_text, model_choice, api_key)
                        
                        if ai_response and ai_audio_data:
                            wave_data = wave_file_from_bytes(ai_audio_data)
                            st.session_state.messages.append({
                                "role": "ai", 
                                "content": ai_response,
                                "audio": wave_data,
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            })
                            
                            # Play AI response immediately
                            st.markdown("#### 🔊 AI Response:")
                            audio_html = create_audio_player(wave_data, autoplay=True)
                            st.markdown(audio_html, unsafe_allow_html=True)
                    
                    st.session_state.recording_status = "ready"
                    time.sleep(2)  # Brief pause before allowing next recording
                    st.rerun()
    
    # Quick actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 New Conversation"):
            st.session_state.messages = []
            st.session_state.recording_status = "ready"
            st.rerun()
    
    with col2:
        if st.button("🎯 Try Sample"):
            # Simulate voice input with sample text
            sample_text = "Hello! Tell me something interesting about space exploration."
            st.session_state.recording_status = "processing"
            
            # Add user message
            st.session_state.messages.append({
                "role": "user", 
                "content": sample_text,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # Get AI response
            with st.spinner("🤖 AI is thinking and generating voice response..."):
                ai_response, audio_data = get_ai_response_with_audio(sample_text, model_choice, api_key)
                
                if ai_response and audio_data:
                    wave_data = wave_file_from_bytes(audio_data)
                    st.session_state.messages.append({
                        "role": "ai", 
                        "content": ai_response,
                        "audio": wave_data,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
            
            st.session_state.recording_status = "ready"
            st.rerun()
    
    with col3:
        if st.button("⏸️ Clear Status"):
            st.session_state.recording_status = "ready"
            st.rerun()
    
    # Chat History Display
    st.markdown("---")
    st.markdown("### 💬 Conversation History")
    
    if st.session_state.messages:
        for i, message in enumerate(st.session_state.messages):
            timestamp = message.get("timestamp", "")
            
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>🗣️ You ({timestamp}):</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
                
                # Display user's audio if available
                if "audio" in message:
                    st.markdown("*Your voice recording:*")
                    st.audio(message["audio"], format="audio/wav")
                    
            else:
                st.markdown(f"""
                <div class="chat-message ai-message">
                    <strong>🤖 AI ({timestamp}):</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
                
                # Display AI audio response
                if "audio" in message:
                    st.markdown("*AI voice response:*")
                    audio_html = create_audio_player(message["audio"], key=f"audio_{i}", autoplay=False)
                    st.markdown(audio_html, unsafe_allow_html=True)
    else:
        st.info("🎙️ Start a conversation by clicking 'Hold to Talk' above!")
    
    # Instructions
    st.markdown("---")
    st.markdown("### 📋 How to Use")
    st.markdown("""
    1. **🎤 Click the microphone button** to start recording your voice
    2. **🗣️ Speak clearly** into your microphone (stops automatically after pause)
    3. **🔄 Processing** - Your speech is converted to text
    4. **🤖 AI responds** with both text and voice automatically
    5. **🔊 Listen** to the AI's voice response
    6. **🔄 Continue** the conversation by recording again
    7. **🆕 Start fresh** with 'New Conversation' button
    """)
    
    # Technical info
    st.markdown("### ⚙️ Technical Details")
    st.markdown("""
    - **🎙️ Audio Recording**: Uses `audio-recorder-streamlit` for browser-based recording
    - **🔄 Speech-to-Text**: Google Speech Recognition API
    - **🧠 AI Processing**: Google Gemini models
    - **🔊 Text-to-Speech**: Google Gemini TTS with Fenrir voice
    - **📱 Compatibility**: Works in modern web browsers with microphone access
    """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1em;">
        <p>🎙️ AI-udio: Full Voice-to-Voice Conversation System<br>
        Powered by Google Gemini TTS | Voice: Fenrir (Excitable)<br>
        🔊 Audio Input ↔️ Audio Output | 🌍 Multi-language Support</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main application entry point"""
    if not check_authentication():
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()