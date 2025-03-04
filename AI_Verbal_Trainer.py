import streamlit as st
import google.generativeai as genai
import speech_recognition as sr
import pyttsx3
import os
import docx
import json
import tempfile
import random
import unittest

def main():
    # Load API Key from docx file
    def load_api_key():
        try:
            doc = docx.Document("/home/harsha/Downloads/Gemini -API.docx")
            return doc.paragraphs[0].text.strip()
        except FileNotFoundError:
            st.error("API key file not found. Please ensure 'api_key.docx' exists.")
        except Exception as e:
            st.error(f"Error reading API key: {str(e)}")
        return None

    API_KEY = load_api_key()
    if API_KEY:
        genai.configure(api_key=API_KEY)
    else:
        st.stop()

    # Initialize Text-to-Speech
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)

    def speak_text(text):
        if isinstance(text, (list, dict)):
            text = str(text)
        engine.say(text)
        engine.runAndWait()

    # Initialize Speech Recognition
    recognizer = sr.Recognizer()

    # Streamlit UI
    st.title("Verbal Communication Skills Trainer")

    # Onboarding Instructions
    st.info("Welcome to the Verbal Communication Skills Trainer! Choose a module and input method to get started.")

    # User Progress Tracking
    PROGRESS_FILE = "progress.json"

    def save_progress(user_input, feedback):
        data = []
        if os.path.exists(PROGRESS_FILE) and os.stat(PROGRESS_FILE).st_size > 0:
            with open(PROGRESS_FILE, "r") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = []
        data.append({"user_input": user_input, "feedback": feedback})
        with open(PROGRESS_FILE, "w") as file:
            json.dump(data, file, indent=4)

    def load_progress():
        if not os.path.exists(PROGRESS_FILE) or os.stat(PROGRESS_FILE).st_size == 0:
            return "No progress recorded yet."
        try:
            with open(PROGRESS_FILE, "r") as file:
                data = json.load(file)
                if data:
                    return "\n\n".join([
                        f"**User Input:**\n{entry['user_input']}\n\n**AI Feedback:**\n{entry['feedback']}\n{'-'*40}"
                        for entry in data
                    ])
                return "No progress recorded yet."
        except json.JSONDecodeError:
            return "No progress recorded yet."

    # Training Modules
    st.subheader("Training Modules")
    module = st.selectbox("Choose a module:", ["Impromptu Speaking", "Storytelling", "Conflict Resolution", "General Feedback"])

    if module != "General Feedback":
        placeholder_text = ""
        if module == "Impromptu Speaking":
            placeholder_text = "Example: Teamwork is essential because it allows people to collaborate, share ideas, and solve problems efficiently."
        elif module == "Storytelling":
            placeholder_text = "Example: One day, I found an old map in my attic. It led me to a hidden treasure chest in my backyard!"
        elif module == "Conflict Resolution":
            placeholder_text = "Example: I understand that deadlines can be challenging. Let's discuss how we can avoid missing them in the future."

        if st.button("Start Training"):
            topic = random.choice([
                "Explain why teamwork is important.",
                "Describe your favorite book and why you love it.",
                "How would you handle a disagreement with a colleague?",
                "Tell a short story about an unexpected adventure.",
                "Convince someone to adopt a healthy habit."
            ])
            st.write(f"**Your Topic:** {topic}")

            # Input Method Selection
            input_method = st.radio("Select Input Method:", ["Text Input", "Voice Input", "Upload Audio File"], key='training_input')
            user_input = ""

            if input_method == "Text Input":
                user_input = st.text_area("Enter your response:", placeholder=placeholder_text, key="training_text_input")

            elif input_method == "Voice Input":
                if "training_voice_input" not in st.session_state:
                    st.session_state["training_voice_input"] = ""
                if "training_listening" not in st.session_state:
                    st.session_state["training_listening"] = False

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Start Voice Input", key="training_start_voice_input"):
                        st.session_state["training_listening"] = True
                        try:
                            with sr.Microphone() as source:
                                recognizer.adjust_for_ambient_noise(source, duration=1)
                                st.info("Listening... Press 'Stop Voice Input' to end.")
                                while st.session_state["training_listening"]:
                                    try:
                                        audio = recognizer.listen(source)
                                        text = recognizer.recognize_google(audio)
                                        if text:
                                            st.session_state["training_voice_input"] += " " + text
                                            st.write(f"You said: {st.session_state['training_voice_input']}")
                                    except sr.UnknownValueError:
                                        st.warning("Could not understand audio.")
                                    except sr.RequestError:
                                        st.warning("Speech recognition service error.")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                        except OSError as e:
                            st.error(f"Error accessing microphone: {e}. Please check permissions or device connection.")
                        except Exception as e:
                            st.error(f"An unexpected error occurred: {e}")
                with col2:
                    if st.button("Stop Voice Input", key="training_stop_voice_input"):
                        st.session_state["training_listening"] = False
                        st.success("Voice input stopped.")
                user_input = st.session_state["training_voice_input"]

            elif input_method == "Upload Audio File":
                uploaded_file = st.file_uploader("Upload Audio File", type=["wav", "mp3", "flac"], key="training_audio_upload")

                if uploaded_file is not None:
                    with tempfile.NamedTemporaryFile(delete=False) as temp_audio:
                        temp_audio.write(uploaded_file.read())
                        temp_file_path = temp_audio.name

                    try:
                        with sr.AudioFile(temp_file_path) as source:
                            audio_data = recognizer.record(source)
                            user_input = recognizer.recognize_google(audio_data)
                        st.write("**Transcribed Text:**", user_input)
                    except sr.UnknownValueError:
                        st.error("Speech recognition could not understand audio")
                    except sr.RequestError as e:
                        st.error(f"Could not request results from Google Speech Recognition service; {e}")
                    except FileNotFoundError:
                        st.error("The uploaded file could not be found.")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                    finally:
                        os.unlink(temp_file_path)

            if st.button("Evaluate Response"):
                if user_input:
                    try:
                        model = genai.GenerativeModel("gemini-1.5-pro")
                        feedback = model.generate_content(f"""Analyze the following response and provide structured feedback (clarity, tone, engagement scores out of 10) on its clarity, structure, engagement, and effectiveness:\n\n{user_input}""")
                        feedback_text = str(feedback.candidates[0].content)

                        # Structured Feedback with Scores
                        scores = extract_scores(feedback_text)
                        structured_feedback = f"""
    **Feedback:**

    **Clarity Score:** {scores['clarity']} / 10
    **Tone Score:** {scores['tone']} / 10
    **Engagement Score:** {scores['engagement']} / 10

    **Strengths:**
    {get_strengths(feedback_text)}

    **Areas for Improvement:**
    {get_improvements(feedback_text)}

    **Overall:**
    {get_overall(feedback_text)}
                        """

                        st.markdown(structured_feedback)
                        speak_text(feedback_text)
                        save_progress(user_input, feedback_text)
                    except Exception as e:
                        st.error(f"Error generating feedback: {str(e)}")
                else:
                    st.warning("Please enter or speak your response to get feedback.")

    else: #general feedback
        # Input Method Selection
        input_method = st.radio("Select Input Method:", ["Text Input", "Voice Input", "Upload Audio File"], key='general_input')
        user_input = ""

        if input_method == "Text Input":
            user_input = st.text_area("Enter your message:", placeholder="Example: I often struggle with filler words like 'um' and 'uh'. How can I improve?", key="general_text_input")

        elif input_method == "Voice Input":
            if "general_voice_input" not in st.session_state:
                st.session_state["general_voice_input"] = ""
            if "general_listening" not in st.session_state:
                st.session_state["general_listening"] = False

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Start Voice Input", key="general_start_voice_input"):
                    st.session_state["general_listening"] = True
                    try:
                        with sr.Microphone() as source:
                            recognizer.adjust_for_ambient_noise(source, duration=1)
                            st.info("Listening... Press 'Stop Voice Input' to end.")
                            while st.session_state["general_listening"]:
                                try:
                                    audio = recognizer.listen(source)
                                    text = recognizer.recognize_google(audio)
                                    if text:
                                        st.session_state["general_voice_input"] += " " + text
                                        st.write(f"You said: {st.session_state['general_voice_input']}")
                                except sr.UnknownValueError:
                                    st.warning("Could not understand audio.")
                                except sr.RequestError:
                                    st.warning("Speech recognition service error.")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                    except OSError as e:
                        st.error(f"Error accessing microphone: {e}. Please check permissions or device connection.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")
                with col2:
                    if st.button("Stop Voice Input", key="general_stop_voice_input"):
                        st.session_state["general_listening"] = False
                        st.success("Voice input stopped.")
                user_input = st.session_state["general_voice_input"]

        elif input_method == "Upload Audio File":
            uploaded_file = st.file_uploader("Upload Audio File", type=["wav", "mp3", "flac"], key="general_audio_upload")

            if uploaded_file is not None:
                with tempfile.NamedTemporaryFile(delete=False) as temp_audio:
                    temp_audio.write(uploaded_file.read())
                    temp_file_path = temp_audio.name

                try:
                    with sr.AudioFile(temp_file_path) as source:
                        audio_data = recognizer.record(source)
                        user_input = recognizer.recognize_google(audio_data)
                    st.write("**Transcribed Text:**", user_input)
                except sr.UnknownValueError:
                    st.error("Speech recognition could not understand audio")
                except sr.RequestError as e:
                    st.error(f"Could not request results from Google Speech Recognition service; {e}")
                except FileNotFoundError:
                    st.error("The uploaded file could not be found.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                finally:
                    os.unlink(temp_file_path)

        if st.button("Get AI Feedback", key="general_feedback_button"):
            if user_input:
                try:
                    model = genai.GenerativeModel("gemini-1.5-pro")
                    feedback = model.generate_content(f"Provide structured feedback (clarity, tone, engagement scores out of 10) on my verbal clarity: {user_input}")
                    feedback_text = str(feedback.candidates[0].content)

                    # Structured Feedback with Scores
                    scores = extract_scores(feedback_text)
                    structured_feedback = f"""
    **Feedback:**

    **Clarity Score:** {scores['clarity']} / 10
    **Tone Score:** {scores['tone']} / 10
    **Engagement Score:** {scores['engagement']} / 10

    **Strengths:**
    {get_strengths(feedback_text)}

    **Areas for Improvement:**
    {get_improvements(feedback_text)}

    **Overall:**
    {get_overall(feedback_text)}
                    """

                    st.markdown(structured_feedback)
                    speak_text(feedback_text)
                    save_progress(user_input, feedback_text)
                except Exception as e:
                    st.error(f"Error generating AI feedback: {str(e)}")
            else:
                st.warning("Please provide input to get feedback.")

    # Show progress history at the end
    st.subheader("Progress History")
    st.text_area("Recorded Progress:", load_progress(), height=200, key="progress_history")

def extract_scores(feedback_text):
    scores = {"clarity": "N/A", "tone": "N/A", "engagement": "N/A"}
    lines = feedback_text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if "clarity score" in line_lower:
            try:
                score_str = line_lower.split("clarity score:")[1].split("/")[0].strip()
                scores["clarity"] = int(score_str)
            except (ValueError, IndexError):
                print(f"Error parsing clarity score from: {line}")
        elif "tone score" in line_lower:
            try:
                score_str = line_lower.split("tone score:")[1].split("/")[0].strip()
                scores["tone"] = int(score_str)
            except (ValueError, IndexError):
                print(f"Error parsing tone score from: {line}")
        elif "engagement score" in line_lower:
            try:
                score_str = line_lower.split("engagement score:")[1].split("/")[0].strip()
                scores["engagement"] = int(score_str)
            except (ValueError, IndexError):
                print(f"Error parsing engagement score from: {line}")
    return scores
def get_strengths(feedback_text):
    strengths = []
    lines = feedback_text.split('\n')
    for line in lines:
        if "strength" in line.lower() or "positive" in line.lower() or "good" in line.lower() or "well" in line.lower():
            if ":" in line:
                strength = line.split(":", 1)[1].strip()
                if strength:
                    strengths.append(f"- {strength}")
    return "\n".join(strengths) if strengths else "- No specific strengths identified."

def get_improvements(feedback_text):
    improvements = []
    lines = feedback_text.split('\n')
    for line in lines:
        if "improve" in line.lower() or "area" in line.lower() or "suggestion" in line.lower() or "could" in line.lower() or "consider" in line.lower():
            if ":" in line:
                improvement = line.split(":", 1)[1].strip()
                if improvement:
                    improvements.append(f"- {improvement}")
    return "\n".join(improvements) if improvements else "- No specific areas for improvement identified."

def get_overall(feedback_text):
    overall = []
    lines = feedback_text.split('\n')
    for line in lines:
        if "overall" in line.lower() or "summary" in line.lower() or "conclusion" in line.lower():
            if ":" in line:
                overall_text = line.split(":", 1)[1].strip()
                if overall_text:
                    overall.append(f"{overall_text}")
    return "\n".join(overall) if overall else "No overall summary provided."

# Unit/Integration Tests
class TestVerbalTrainer(unittest.TestCase):

    def test_extract_scores(self):
        feedback_text = "Clarity Score: 8/10\nTone Score: 7/10\nEngagement Score: 9/10"
        scores = extract_scores(feedback_text)
        self.assertEqual(scores["clarity"], 8)
        self.assertEqual(scores["tone"], 7)
        self.assertEqual(scores["engagement"], 9)

    def test_extract_scores_with_na(self):
        feedback_text = "Some random text. No scores here."
        scores = extract_scores(feedback_text)
        self.assertEqual(scores["clarity"], "N/A")
        self.assertEqual(scores["tone"], "N/A")
        self.assertEqual(scores["engagement"], "N/A")

    def test_extract_scores_partial(self):
        feedback_text = "Clarity Score: 6/10\nSome other text."
        scores = extract_scores(feedback_text)
        self.assertEqual(scores["clarity"], 6)
        self.assertEqual(scores["tone"], "N/A")
        self.assertEqual(scores["engagement"], "N/A")

    def test_get_strengths_found(self):
        feedback_text = "Strength: Good clarity.\nPositive: Well-structured."
        strengths = get_strengths(feedback_text)
        self.assertIn("- Good clarity.", strengths)
        self.assertIn("- Well-structured.", strengths)

    def test_get_strengths_not_found(self):
        feedback_text = "No strengths mentioned."
        strengths = get_strengths(feedback_text)
        self.assertEqual(strengths, "- No specific strengths identified.")

    def test_get_improvements_found(self):
        feedback_text = "Improve: Use more concise language.\nArea: Consider varying your tone."
        improvements = get_improvements(feedback_text)
        self.assertIn("- Use more concise language.", improvements)
        self.assertIn("- Consider varying your tone.", improvements)

    def test_get_improvements_not_found(self):
        feedback_text = "No improvements mentioned."
        improvements = get_improvements(feedback_text)
        self.assertEqual(improvements, "- No specific areas for improvement identified.")

    def test_get_overall_found(self):
        feedback_text = "Overall: A solid performance.\nSummary: Good job!"
        overall = get_overall(feedback_text)
        self.assertIn("A solid performance.", overall)
        self.assertIn("Good job!", overall)

    def test_get_overall_not_found(self):
        feedback_text = "No overall feedback."
        overall = get_overall(feedback_text)
        self.assertEqual(overall, "No overall summary provided.")

if __name__ == "__main__":
    main()
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
