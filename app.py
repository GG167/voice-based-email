from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from gtts import gTTS
import speech_recognition as sr
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import tempfile

# Load environment variables (EMAIL_USER, EMAIL_PASSWORD)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")

# ------------------- LOGIN PAGE -------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == os.getenv("EMAIL_USER") and password == os.getenv("EMAIL_PASSWORD"):
            session['logged_in'] = True
            return redirect(url_for("compose"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

# ------------------- COMPOSE EMAIL PAGE -------------------
@app.route("/compose", methods=["GET", "POST"])
def compose():
    if 'logged_in' not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        recipient = request.form.get("recipient")
        subject = request.form.get("subject")
        body = request.form.get("body")

        msg = EmailMessage()
        msg['From'] = os.getenv("EMAIL_USER")
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                smtp.send_message(msg)
            return render_template("compose.html", success="Email sent successfully!")
        except Exception as e:
            return render_template("compose.html", error=f"Error sending email: {e}")

    return render_template("compose.html")

# ------------------- AUDIO UPLOAD / SPEECH TO TEXT -------------------
@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    """Convert uploaded audio to text"""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    audio_file = request.files['file']
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
        return jsonify({"text": text})
    except sr.UnknownValueError:
        return jsonify({"error": "Could not understand audio"}), 400
    except sr.RequestError:
        return jsonify({"error": "Error connecting to recognition service"}), 500

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
