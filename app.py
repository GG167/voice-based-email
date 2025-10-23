import streamlit as st
from gtts import gTTS
import speech_recognition as sr
import smtplib
from email.message import EmailMessage
import os
import tempfile

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Voice Based Email", page_icon="✉️", layout="wide")
st.title("🎙️ Voice Based Email for the Blind")

# ------------------ UTILITY FUNCTIONS ------------------
def text_to_speech(text):
    """Converts text to speech and plays it."""
    try:
        tts = gTTS(text=text, lang="en")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)
        audio_bytes = open(temp_file.name, "rb").read()
        st.audio(audio_bytes, format="audio/mp3")
        os.remove(temp_file.name)
    except Exception as e:
        st.error(f"Speech synthesis failed: {e}")

def speech_to_text(audio_file):
    """Converts an uploaded audio file (wav/mp3) into text."""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""
    except Exception as e:
        st.error(f"Error in speech recognition: {e}")
        return ""

def send_email(sender_email, sender_password, recipient, subject, body):
    """Sends an email using Gmail SMTP."""
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# ------------------ LOGIN ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.subheader("🔐 Login to Your Gmail Account")
    email = st.text_input("Email Address")
    password = st.text_input("App Password (not your main Gmail password)", type="password")

    if st.button("Login"):
        if email and password:
            st.session_state.logged_in = True
            st.session_state.email = email
            st.session_state.password = password
            st.success("Login successful!")
            text_to_speech("Login successful. You can now compose your email.")
        else:
            st.error("Please enter both email and password.")

# ------------------ MAIN EMAIL APP ------------------
if st.session_state.logged_in:
    st.subheader("✉️ Compose and Send Email")

    recipient = st.text_input("Recipient's Email")
    subject = st.text_input("Subject")
    body = st.text_area("Body")

    # Optional: Voice input for body
    st.markdown("🎤 **Upload a voice file (WAV or MP3) to input email body automatically:**")
    audio_file = st.file_uploader("Upload audio", type=["wav", "mp3"])

    if audio_file is not None:
        st.info("Processing uploaded audio file...")
        recognized_text = speech_to_text(audio_file)
        if recognized_text:
            st.success(f"Recognized text: {recognized_text}")
            body = recognized_text
        else:
            st.warning("Sorry, could not recognize speech from the uploaded file.")

    if st.button("Send Email"):
        if recipient and subject and body:
            success = send_email(
                st.session_state.email,
                st.session_state.password,
                recipient,
                subject,
                body
            )
            if success:
                st.success("✅ Email sent successfully!")
                text_to_speech("Your email has been sent successfully.")
        else:
            st.error("Please fill in all fields before sending.")

    st.markdown("---")
    st.markdown("### Other Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Search Latest Emails (Demo)"):
            st.info("This feature is under development.")
            text_to_speech("Searching your latest five emails. Please wait.")
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.experimental_rerun()

st.markdown("---")
st.caption("Developed by Goutham | Voice Based Email System 🧠🎧")
