import streamlit as st
import os
import json
from google.cloud import speech, texttospeech
import google.generativeai as genai
import speech_recognition as sr
import docx

# Load API Key from docx file
def get_api_key_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        return doc.paragraphs[0].text.strip()
    except Exception as e:
        st.error(f"Failed to read API key from document: {e}")
        return None

API_KEY = get_api_key_from_docx("/home/harsha/Downloads/Gemini -API.docx")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.stop()

# Set up authentication for Google Cloud
if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/harsha/Downloads/verbal_trainer.json"

# Initialize Google Cloud clients
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

# Progress log storage
LOG_FILE = "progress_log.json"
def save_progress(log_entry):
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        else:
            logs = []
        logs.append(log_entry)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=4)
    except Exception as e:
        st.error("Failed to save progress.")

def load_progress():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

st.title("Verbal Communication Skills Trainer")

# Chat-based training
st.header("Chat with AI Coach")
user_input = st.text_area("You:", "")
if st.button("Send") and user_input:
    response = genai.GenerativeModel("gemini-1.5-pro-latest").generate_content(f"You are a communication coach. Provide detailed and constructive feedback on: {user_input}").text
    st.write("AI Coach:", response)
    save_progress({"type": "chat", "input": user_input, "feedback": response})

# Voice-based training
st.write("Click the button and start speaking...")
recognizer = sr.Recognizer()

if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = []
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""

if st.button("Start Recording") and not st.session_state.recording:
    st.session_state.recording = True
    st.session_state.audio_data = []
    st.session_state.transcription = ""
    st.write("Listening... Click 'Stop Recording' to finish.")

if st.session_state.recording:
    with sr.Microphone() as source:
        try:
            audio = recognizer.listen(source, timeout=3)
            st.session_state.audio_data.append(audio)
            try:
                text = recognizer.recognize_google(audio)
                st.session_state.transcription += " " + text
                st.text_area("You:", value=st.session_state.transcription)
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                st.write("Error with the speech recognition service.")
        except sr.WaitTimeoutError:
            pass

if st.button("Stop Recording") and st.session_state.recording:
    st.session_state.recording = False
    full_audio = sr.AudioData(b"".join(a.frame_data for a in st.session_state.audio_data), source.SAMPLE_RATE, source.SAMPLE_WIDTH)
    try:
        text_output = recognizer.recognize_google(full_audio)
        st.write("Transcription:", text_output)
        response = genai.GenerativeModel("gemini-1.5-pro-latest").generate_content(f"Analyze this speech in detail, providing feedback on clarity, pronunciation, and confidence: {text_output}").text
        st.write("AI Feedback:", response)
        save_progress({"type": "voice", "transcription": text_output, "feedback": response})
    except sr.UnknownValueError:
        st.write("Sorry, could not understand the speech.")
    except sr.RequestError:
        st.write("Error with the speech recognition service.")

# Skill Training Modules
st.header("Skill Training Modules")
training_type = st.selectbox("Select a training type", ["Impromptu Speaking", "Storytelling", "Conflict Resolution"])
if st.button("Start Training"):
    if training_type == "Impromptu Speaking":
        topic = "Explain why teamwork is important."
    elif training_type == "Storytelling":
        topic = "Tell a short story about a lesson you learned."
    else:
        topic = "Respond to: 'I'm upset because you missed a deadline.'"
    st.write("Your topic:", topic)
    user_response = st.text_area("Your Response:", key="user_response_area")
    if st.button("Get Feedback"):
        response = genai.GenerativeModel("gemini-1.5-pro-latest").generate_content(f"Analyze this response and provide specific, actionable feedback on content, structure, and tone: {user_response}").text
        st.write("AI Feedback:", response)
        save_progress({"type": "training", "module": training_type, "response": user_response, "feedback": response})

# View Progress
if st.button("View Progress"):
    progress_logs = load_progress()
    if progress_logs:
        st.json(progress_logs)
    else:
        st.write("No progress recorded yet.")
