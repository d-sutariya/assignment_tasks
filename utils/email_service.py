import smtplib
from email.message import EmailMessage
from config import Config

def send_email(email, otp):
    """Send OTP via Gmail SMTP"""
    try:
        msg = EmailMessage()
        msg["Subject"] = "Your OTP Code"
        msg["From"] = Config.GMAIL_USER
        msg["To"] = email
        msg.set_content(f"Your OTP is: {otp}. It is valid for 5 minutes.")

        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.GMAIL_USER, Config.GMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False
