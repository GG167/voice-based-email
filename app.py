from flask import Flask, render_template, request, redirect, session, url_for, send_file
from gtts import gTTS
import speech_recognition as sr
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import tempfile

load_dotenv()  # load EMAIL_USER, EMAIL_PASSWORD

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == os.getenv("EMAIL_USER") and password == os.getenv("EMAIL_PASSWORD"):
            session['logged_in'] = True
            return redirect(url_for("compose"))
    return render_template("login.html")

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
            return "Email sent successfully!"
        except Exception as e:
            return f"Error sending email: {e}"

    return render_template("compose.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
