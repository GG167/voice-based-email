# homepage/views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
import imaplib
import email
from email.header import decode_header
import smtplib  
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import speech_recognition as sr
from gtts import gTTS
from pygame import mixer
import os
import re
import uuid


import io
from gtts import gTTS
import pygame

def text_to_speech(text):
    """Convert text to speech and play it directly from memory without saving any files."""
    try:
        # Convert text to speech (in memory)
        mp3_fp = io.BytesIO()
        tts = gTTS(text=text, lang='en', slow=False)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # Initialize pygame mixer once
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # Load and play from memory
        pygame.mixer.music.load(mp3_fp, 'mp3')
        pygame.mixer.music.play()

        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.music.unload()

    except Exception as e:
        print(f"An error occurred in text_to_speech: {e}")

def speech_to_text(duration=5):
    """Listens for speech and converts it to text."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        try:
            # Play notification sound before listening
            mixer.pre_init(44100, -16, 2, 512)
            mixer.init()

            mixer.music.load('speak.mp3')
            mixer.music.play()
            while mixer.music.get_busy():
                continue
            mixer.music.stop()
            mixer.quit()
        except Exception as e:
            print(f"Could not play speak.mp3 notification: {e}")

        try:
            audio = r.listen(source, phrase_time_limit=duration)
            response = r.recognize_google(audio)
            return response
        except sr.UnknownValueError:
            text_to_speech("Sorry, I could not understand that.")
            return None
        except sr.RequestError as e:
            text_to_speech("Could not request results; check your connection.")
            print(f"Speech recognition error: {e}")
            return None


def get_confirmed_speech_input(prompt, duration=10):
    """A helper to ask a user for voice input and confirm it."""
    while True:
        text_to_speech(prompt)
        response = speech_to_text(duration)
        
        if response:
            text_to_speech(f"You said: {response}. Is that correct? Please say yes or no.")
            confirmation = speech_to_text(3)
            
            # --- THIS IS THE CORRECTED PART ---
            # We now check for multiple ways of saying "yes".
            if confirmation:
                positive_words = ['yes', 'yeah', 'correct', 'yep', 'confirm']
                # Check if any of the positive words were said
                if any(word in confirmation.lower() for word in positive_words):
                    return response # Return the original response if confirmed
            
            text_to_speech("Okay, let's try that again.")
        # If the initial response was not understood, the loop will repeat automatically# --- Email and System Helper Functions ---

def convert_special_char(text):
    """Cleans up spoken email addresses and passwords."""
    text = text.lower().replace(' ', '')
    replacements = {
        'attherate': '@', 'dot': '.', 'underscore': '_', 'dollar': '$', 'hash': '#',
        'star': '*', 'plus': '+', 'minus': '-', 'dash': '-'
    }
    for word, char in replacements.items():
        text = text.replace(word, char)
    return text

def get_email_connections(request):
    """Retrieves credentials from the session and returns SMTP and IMAP connections."""
    email_address = request.session.get('email_address')
    app_password = request.session.get('app_password')

    if not email_address or not app_password:
        return None, None
    try:
        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
        smtp_server.starttls()
        
        smtp_server.login(email_address, app_password)

        imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
        imap_server.login(email_address, app_password)
        
        return smtp_server, imap_server
    except Exception as e:
        print(f"Failed to create email connections: {e}")
        return None, None
        
def clean_header(header):
    """Decodes email headers to a readable string."""
    if header is None:
        return ""
    decoded_header = decode_header(header)
    header_parts = []
    for part, encoding in decoded_header:
        if isinstance(part, bytes):
            header_parts.append(part.decode(encoding or 'utf-8', 'ignore'))
        else:
            header_parts.append(part)
    return "".join(header_parts)

# --- Django Views ---

# In homepage/views.py, replace your login_view with this corrected version

def login_view(request):
    """Handles voice-based login only."""
    if request.method == 'POST':
        text_to_speech("Welcome to Voice Based Email. Please log in to continue.")

        # Get email via voice
        email_address = get_confirmed_speech_input("Please say your full email address.", duration=15)
        if not email_address:
            return render(request, 'homepage/login.html', {'error_message': 'Could not get email.'})
        cleaned_email = convert_special_char(email_address)

        # Get password via voice
        text_to_speech("For Gmail, it is recommended to use an App Password.")
        password = get_confirmed_speech_input("Please say your password.", duration=30)
        if not password:
            return render(request, 'homepage/login.html', {'error_message': 'Could not get password.'})
        cleaned_password = convert_special_char(password)

        # Try IMAP and SMTP login
        try:
            # IMAP verification
            imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
            imap_server.login(cleaned_email, cleaned_password)
            imap_server.logout()

            # SMTP verification
            smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
            smtp_server.starttls()
            smtp_server.login(cleaned_email, cleaned_password)
            smtp_server.quit()

            # Save session and redirect
            request.session['email_address'] = cleaned_email
            request.session['app_password'] = cleaned_password
            text_to_speech("Congratulations! You have logged in successfully.")
            return redirect('homepage:options')

        except Exception as e:
            print(f"Voice login failed for {cleaned_email}: {e}")
            text_to_speech("Invalid login details. Please try again.")
            return render(request, 'homepage/login.html', {'error_message': 'Invalid credentials.'})

    # GET request: show login page
    return render(request, 'homepage/login.html')

def options_view(request):
    """Provides user with main menu options after logging in."""
    if 'email_address' not in request.session:
        return redirect('login_view')

    if request.method == 'POST':
        prompt = "What would you like to do? Say 'compose', 'inbox', 'sent messages', 'trash or garbage', 'delete', or 'logout'."
        text_to_speech(prompt)
        action = speech_to_text(5)  # listen for voice command
        
        if action:
            action = action.lower()
            if 'compose' in action:
                return JsonResponse({'result': 'compose'})
            if 'inbox' in action:
                return JsonResponse({'result': 'inbox'})
            if 'sent' in action or 'messages' in action:
                return JsonResponse({'result': 'sent'})
            if 'trash' in action or 'garbage' in action:
                return JsonResponse({'result': 'trash'})
            if 'delete' in action or 'remove' in action:  # supports both words
                return JsonResponse({'result': 'delete'})
            if 'log out' in action or 'logout' in action:
                request.session.flush()
                text_to_speech("You have been successfully logged out.")
                return JsonResponse({'result': 'logout'})
        
        # If none matched, ask user to try again
        text_to_speech("Invalid action. Please try again.")
        return JsonResponse({'result': 'failure'})

    return render(request, 'homepage/options.html')

def compose_view(request):
    """Handles composing and sending a new email."""
    if 'email_address' not in request.session: return redirect('login_view')
    if request.method == 'POST':
        smtp, _ = get_email_connections(request)
        if not smtp:
            text_to_speech("Your session may have expired. Please log in again.")
            return JsonResponse({'result': 'logout'})
        from_address = request.session['email_address']
        
        recipient_str = get_confirmed_speech_input("Who is the recipient?", duration=15)
        recipient = convert_special_char(recipient_str)
        subject = get_confirmed_speech_input("What is the subject?", duration=20)
        body = get_confirmed_speech_input("What should the email say?", duration=60)

        msg = MIMEMultipart()
        msg['From'] = from_address
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            smtp.sendmail(from_address, [recipient], msg.as_string())
            text_to_speech("Your email has been sent successfully.")
            smtp.quit()
            return JsonResponse({'result': 'success'})
        except Exception as e:
            print(f"Failed to send email: {e}")
            text_to_speech("Sorry, your email could not be sent.")
            smtp.quit()
            return JsonResponse({'result': 'failure'})
    return render(request, 'homepage/compose.html')

def read_emails(imap, email_ids, max_to_read=5):
    """Helper function to read and announce a list of emails."""
    if not email_ids:
        text_to_speech("This folder is empty.")
        return

    # Read the most recent emails first
    emails_to_read = email_ids[-max_to_read:]
    emails_to_read.reverse()

    text_to_speech(f"Showing the latest {len(emails_to_read)} emails.")
    
    for mail_id in emails_to_read:
        status, data = imap.fetch(mail_id, '(RFC822)')
        raw_email = data[0][1]
        message = email.message_from_bytes(raw_email)
        
        from_ = clean_header(message['From'])
        subject = clean_header(message['Subject'])
        
        text_to_speech(f"Email from: {from_}. Subject: {subject}.")
        # Here you could add logic to ask the user if they want to read the body, reply, etc.

def _speak_chunks(text, chunk_size=500):
    # Helper: speak long text in chunks so TTS doesn't choke
    for i in range(0, len(text), chunk_size):
        text_to_speech(text[i:i+chunk_size])

def _extract_plaintext(msg):
    # Helper: get readable body from an email.message.Message
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = part.get("Content-Disposition", "")
            if ctype == "text/plain" and "attachment" not in (disp or "").lower():
                try:
                    parts.append(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore"))
                except Exception:
                    continue
        return "\n".join(parts).strip()
    else:
        try:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore").strip()
        except Exception:
            return ""

def sent_view(request):
    """
    Reads the 5 latest emails from the Sent folder and announces:
      - Recipient (To)
      - Subject
      - Date and Time
    """
    if 'email_address' not in request.session:
        return redirect('login_view')

    if request.method == 'POST':
        _, imap = get_email_connections(request)
        if not imap:
            text_to_speech("Session expired. Please log in again.")
            return JsonResponse({'result': 'logout'})

        try:
            # Select Gmail's Sent Mail folder
            imap.select('"[Gmail]/Sent Mail"')
            status, data = imap.search(None, 'ALL')

            if status != 'OK' or not data[0]:
                text_to_speech("Your sent folder is empty.")
                return JsonResponse({'result': 'success'})

            email_ids = data[0].split()
            top_email_ids = email_ids[-5:]  # get the latest 5
            top_email_ids.reverse()  # newest first

            from email.utils import parsedate_to_datetime

            for eid in top_email_ids:
                status, msg_data = imap.fetch(eid, '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                # Extract fields
                to_field = msg.get('to') or "Unknown recipient"
                subject = msg.get('subject') or "No subject"
                date_field = msg.get('date') or "Unknown date"

                # Format the date properly
                try:
                    parsed_date = parsedate_to_datetime(date_field)
                    formatted_date = parsed_date.strftime("%A, %d %B %Y at %I:%M %p")
                except Exception:
                    formatted_date = date_field

                # Announce details clearly
                text_to_speech(f"Email sent to {to_field}. Subject: {subject}. Sent on {formatted_date}.")

            text_to_speech("These were your five most recent sent emails.")

        except Exception as e:
            print(f"Error reading sent mail: {e}")
            text_to_speech("Could not access your sent folder.")
        finally:
            try:
                if imap:
                    imap.close()
                    imap.logout()
            except Exception:
                pass

        return JsonResponse({'result': 'success'})

    return render(request, 'homepage/sent.html')

def trash_view(request):
    """
    Voice-based Trash management:
      - Reads the top 5 latest emails from Trash
      - Asks user to 'restore' or 'permanently delete'
      - Performs the action on real mailbox
      - Always processes the latest 5 emails
    """
    if 'email_address' not in request.session:
        return redirect('login_view')

    if request.method == 'POST':
        _, imap = get_email_connections(request)
        if not imap:
            text_to_speech("Session expired. Please log in again.")
            return JsonResponse({'result': 'logout'})

        try:
            from email.utils import parsedate_to_datetime

            # Select Gmail Trash folder
            imap.select('"[Gmail]/Trash"')
            status, data = imap.search(None, 'ALL')

            if status != 'OK' or not data[0]:
                text_to_speech("Your trash folder is empty.")
                return JsonResponse({'result': 'success'})

            email_ids = data[0].split()
            top_email_ids = email_ids[-5:]  # latest 5 emails
            top_email_ids.reverse()  # newest first

            for eid in top_email_ids:
                # Fetch full email
                s, msg_data = imap.fetch(eid, '(RFC822)')
                if s != 'OK':
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                from_field = msg.get('from') or "Unknown sender"
                subject = msg.get('subject') or "No subject"
                date_field = msg.get('date') or "Unknown date"

                # Format date
                try:
                    parsed_date = parsedate_to_datetime(date_field)
                    formatted_date = parsed_date.strftime("%A, %d %B %Y at %I:%M %p")
                except Exception:
                    formatted_date = date_field

                # Announce email
                text_to_speech(f"Email from {from_field}. Subject: {subject}. Deleted on {formatted_date}.")
                text_to_speech("Say 'restore' to move this email back to inbox, 'permanent delete' to remove it forever, or 'menu' to go back.")

                user_choice = speech_to_text(6)
                if not user_choice:
                    text_to_speech("I did not catch that. Skipping this email.")
                    continue

                user_choice = user_choice.lower()

                # Restore
                if 'restore' in user_choice or 'move back' in user_choice:
                    try:
                        result = imap.copy(eid, "INBOX")
                        if result[0] == 'OK':
                            imap.store(eid, '+FLAGS', '\\Deleted')
                            text_to_speech("Email restored to inbox successfully.")
                        else:
                            text_to_speech("Could not restore this email.")
                    except Exception as restore_err:
                        print("Restore error:", restore_err)
                        text_to_speech("There was a problem restoring the email.")

                # Permanently delete
                elif 'permanent' in user_choice or 'delete' in user_choice:
                    try:
                        imap.store(eid, '+FLAGS', '\\Deleted')
                        text_to_speech("Email marked for permanent deletion.")
                    except Exception as del_err:
                        print("Permanent delete error:", del_err)
                        text_to_speech("Could not delete this email.")

                # Return to menu
                elif 'menu' in user_choice or 'back' in user_choice:
                    text_to_speech("Returning to main menu.")
                    break

                else:
                    text_to_speech("Invalid command. Skipping to next email.")

            # Commit deletions permanently
            imap.expunge()
            text_to_speech("Trash actions completed. Returning to main menu.")

        except Exception as e:
            print(f"Error accessing trash: {e}")
            text_to_speech("An error occurred while managing your trash folder.")
            return JsonResponse({'result': 'failure'})

        finally:
            try:
                imap.close()
                imap.logout()
            except Exception:
                pass

        return JsonResponse({'result': 'success'})

    return render(request, 'homepage/trash.html')


def inbox_view(request):
    """
    Inbox voice interface:
      - Announces options: unread, search, star, back
      - Executes based on speech commands
      - Returns JSON for navigation (inbox/options/logout)
    """
    if 'email_address' not in request.session:
        return redirect('login_view')

    if request.method == 'POST':
        try:
            # Announce options every time
            text_to_speech(
                "Say 'unread' to hear unread emails, "
                "'search' to find an email, "
                "or 'back' to return to the main menu."
            )

            action = speech_to_text(5)
            if not action:
                text_to_speech("I did not catch that. Please try again.")
                return JsonResponse({'result': 'inbox'})

            action = action.lower()

            # ============= UNREAD =============
           # ============= UNREAD =============
            if 'unread' in action:
                _, imap = get_email_connections(request)
                if not imap:
                    text_to_speech("Session expired. Please log in again.")
                    return JsonResponse({'result': 'logout'})

                try:
                    imap.select('INBOX')
                    status, data = imap.search(None, 'UNSEEN')
                    ids = data[0].split() if status == 'OK' else []

                    if not ids:
                        text_to_speech("There are no unread emails.")
                    else:
                        top_ids = ids[-5:]  # Get latest 5 unread
                        for eid in reversed(top_ids):
                            s, msg_data = imap.fetch(eid, '(RFC822)')
                            if s != 'OK':
                                continue

                            msg = email.message_from_bytes(msg_data[0][1])
                            subject = msg.get('subject') or "No subject"
                            from_field = msg.get('from') or "Unknown sender"
                            date_field = msg.get('date') or "Unknown date"

                            # --- Try to parse the date to a friendly format ---
                            try:
                                from email.utils import parsedate_to_datetime
                                parsed_date = parsedate_to_datetime(date_field)
                                formatted_date = parsed_date.strftime("%A, %d %B %Y at %I:%M %p")
                            except Exception:
                                formatted_date = date_field  # fallback to raw header

                            # ---- Extract the email body (prefer plain text) ----
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get('Content-Disposition'))
                                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                                        charset = part.get_content_charset() or 'utf-8'
                                        try:
                                            body = part.get_payload(decode=True).decode(charset, errors='replace')
                                        except Exception:
                                            body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                        break
                            else:
                                charset = msg.get_content_charset() or 'utf-8'
                                try:
                                    body = msg.get_payload(decode=True).decode(charset, errors='replace')
                                except Exception:
                                    body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

                            # ---- Read aloud everything ----
                            text_to_speech(f"From {from_field}.")
                            text_to_speech(f"Received on {formatted_date}.")
                            text_to_speech(f"Subject: {subject}.")

                            if body.strip():
                                text_to_speech("Email content is as follows.")
                                # Optional: limit very long emails
                                text_to_speech(body[:1500])
                            else:
                                text_to_speech("This email has no text content.")

                            # ---- Mark the message as read in real mailbox ----
                            try:
                                imap.store(eid, '+FLAGS', '\\Seen')
                            except Exception as mark_err:
                                print("Could not mark as read:", mark_err)

                        text_to_speech("Finished reading unread emails. Returning to inbox menu.")
                finally:
                    try:
                        imap.close()
                        imap.logout()
                    except Exception:
                        pass

                return JsonResponse({'result': 'inbox'})


            # ============= SEARCH =============
           # ============= SEARCH =============
           # ============= SEARCH =============
            if 'search' in action:
                text_to_speech("Please say the sender name or email address to search.")
                key = speech_to_text(5)
                if not key:
                    text_to_speech("I did not hear the search term. Returning to inbox menu.")
                    return JsonResponse({'result': 'inbox'})

                key_l = key.lower()
                _, imap = get_email_connections(request)
                if not imap:
                    text_to_speech("Session expired. Please log in again.")
                    return JsonResponse({'result': 'logout'})
                
                try:
                    imap.select('INBOX')
                    status, data = imap.search(None, 'ALL')
                    if status != 'OK' or not data[0]:
                        text_to_speech("No emails found in your inbox.")
                        return JsonResponse({'result': 'inbox'})

                    # Get top 5 latest emails
                    email_ids = data[0].split()
                    top5_ids = list(reversed(email_ids[-5:]))

                    found_email = None

                    for eid in top5_ids:
                        status, msg_data = imap.fetch(eid, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])')
                        if status != 'OK':
                            continue

                        raw_msg = msg_data[0][1]
                        msg = email.message_from_bytes(raw_msg)
                        sender = msg.get('from', 'Unknown sender')
                        subject = msg.get('subject', 'No subject')

                        if key_l in sender.lower():
                            found_email = {'eid': eid, 'from': sender, 'subject': subject}
                            break

                    if not found_email:
                        text_to_speech(f"No emails found from {key}. Returning to inbox menu.")
                        return JsonResponse({'result': 'inbox'})

                    # Ask if user wants to read it
                    text_to_speech(f"Found an email from {found_email['from']}. Subject: {found_email['subject']}. Do you want me to read it fully? Say yes or no.")
                    confirm = speech_to_text(5)

                    if confirm and 'yes' in confirm.lower():
                        status, full_data = imap.fetch(found_email['eid'], '(RFC822)')
                        if status == 'OK':
                            full_msg = email.message_from_bytes(full_data[0][1])
                            
                            # Extract plain text body
                            if full_msg.is_multipart():
                                body = ''
                                for part in full_msg.walk():
                                    if part.get_content_type() == 'text/plain':
                                        body += part.get_payload(decode=True).decode(errors='ignore')
                            else:
                                body = full_msg.get_payload(decode=True).decode(errors='ignore')

                            if not body.strip():
                                text_to_speech("This email has no readable text.")
                            else:
                                body = re.sub(r'\s+', ' ', body)
                                _speak_chunks(body, 600)
                        else:
                            text_to_speech("I could not open that email.")
                    else:
                        text_to_speech("Okay, not reading the full email.")

                    text_to_speech("Returning to inbox menu.")

                finally:
                    try:
                        imap.logout()
                    except Exception:
                        pass

                return JsonResponse({'result': 'inbox'})



            # ============= BACK ============
            if 'back' in action or 'menu' in action:
                text_to_speech("Returning to the main menu.")
                return JsonResponse({'result': 'options'})

            # Unknown command
            text_to_speech("Invalid option. Please say unread, search, star, or back.")
            return JsonResponse({'result': 'inbox'})

        except Exception as e:
            print("Error in inbox_view:", e)
            text_to_speech("An unexpected error occurred in inbox.")
            return JsonResponse({'result': 'inbox'})

    # For GET
    return render(request, 'homepage/inbox.html')


def delete_view(request):
    """
    Reads top 5 newest INBOX emails, announces details, asks for delete confirmation,
    moves selected emails to Bin/Trash in real mailbox, allows continue/menu.
    """
    if 'email_address' not in request.session:
        return redirect('login_view')

    if request.method == 'POST':
        _, imap = get_email_connections(request)
        if not imap:
            text_to_speech("Session expired. Please log in again.")
            return JsonResponse({'result': 'logout'})

        try:
            import email
            from email.utils import parsedate_to_datetime

            # Function to get current top 5 emails from INBOX
            def get_top_5_inbox_emails(imap_conn):
                imap_conn.select('INBOX')
                status, data = imap_conn.search(None, 'ALL')
                if status != 'OK' or not data[0]:
                    return []
                email_ids = data[0].split()
                top_email_ids = email_ids[-5:]  # latest 5
                top_email_ids.reverse()  # newest first
                return top_email_ids

            top_email_ids = get_top_5_inbox_emails(imap)
            if not top_email_ids:
                text_to_speech("Your inbox is empty. Nothing to delete.")
                return JsonResponse({'result': 'success'})

            for eid in top_email_ids:
                # Fetch full email (header + body)
                status, msg_data = imap.fetch(eid, '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                from_field = msg.get('from') or "Unknown sender"
                subject = msg.get('subject') or "No subject"
                date_field = msg.get('date') or "Unknown date"

                # Format date nicely
                try:
                    parsed_date = parsedate_to_datetime(date_field)
                    formatted_date = parsed_date.strftime("%A, %d %B %Y at %I:%M %p")
                except Exception:
                    formatted_date = date_field

                # Announce email details
                text_to_speech(f"Email from {from_field}. Subject: {subject}. Received on {formatted_date}.")
                text_to_speech("Do you want to delete this email? Say yes delete or no delete")

                response = speech_to_text(5)
                if response and "yes" in response.lower() and "delete" in response.lower():
                    try:
                        # Move email from INBOX → Bin/Trash
                        result = imap.copy(eid, "[Gmail]/Trash")  # Gmail
                        if result[0] != "OK":
                            imap.copy(eid, "Trash")  # Outlook/Yahoo fallback

                        # Mark original INBOX email as deleted
                        imap.store(eid, '+FLAGS', '\\Deleted')
                        text_to_speech("Email moved to bin successfully.")
                    except Exception as copy_err:
                        print("Error moving to bin:", copy_err)
                        text_to_speech("Could not move this email to bin. Skipping.")
                else:
                    # Any response that is not "yes delete" is treated as keep
                    text_to_speech("Email kept safely.")


                # Ask user whether to continue deleting or return to menu
                text_to_speech("Do you want to continue deleting other emails, or go back to the menu?")
                next_action = speech_to_text(5)
                if next_action and "menu" in next_action.lower():
                    text_to_speech("Returning to main menu.")
                    break
                elif not next_action or "continue" not in next_action.lower():
                    text_to_speech("No valid response. Returning to main menu.")
                    break

            # Commit deletions in INBOX (actually removes emails)
            imap.expunge()
            text_to_speech("Selected emails have been moved to bin in your inbox.")

        except Exception as e:
            print(f"Error deleting emails: {e}")
            text_to_speech("An error occurred while moving emails to bin.")
            return JsonResponse({'result': 'failure'})

        finally:
            try:
                imap.close()
                imap.logout()
            except Exception:
                pass

        return JsonResponse({'result': 'success'})

    return render(request, 'homepage/delete.html')




