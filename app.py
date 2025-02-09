import random
import smtplib
import time
from flask import Flask, request, jsonify
from email.message import EmailMessage
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MY_GMAIL = os.getenv("MY_GMAIL")

# SMTP Server Details
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = MY_GMAIL
APP_PASSWORD = GMAIL_APP_PASSWORD

app = Flask(__name__)

# Store OTPs in memory (For production, use a database)
otp_storage = {}

# Function to generate a 6-digit OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# Function to send OTP via email
def send_otp_email(email, otp):
    try:
        msg = EmailMessage()
        msg.set_content(f"Your OTP for verification is: {otp}")
        msg["Subject"] = "Your OTP Code"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(EMAIL_ADDRESS, APP_PASSWORD)  # Log in with App Password
            server.send_message(msg)

        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

# API to generate and send OTP
@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    otp = generate_otp()  # Generate OTP
    current_time = time.time()  # Store current timestamp

    # Store OTP details (expires in 5 minutes, max 5 attempts)
    otp_storage[email] = {
        "otp": otp,
        "expires_at": current_time + 300,  # 300 seconds = 5 minutes
        "attempts_left": 5
    }

    if send_otp_email(email, otp):
        return jsonify({"message": "OTP sent successfully"}), 200
    else:
        return jsonify({"error": "Failed to send OTP"}), 500

# API to verify OTP
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get("email")
    user_otp = data.get("otp")

    if not email or not user_otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    otp_data = otp_storage.get(email)

    if not otp_data:
        return jsonify({"error": "No OTP found. Request a new one."}), 400

    # Check if OTP is expired
    if time.time() > otp_data["expires_at"]:
        otp_storage.pop(email)
        return jsonify({"error": "OTP has expired. Request a new one."}), 400

    # Check attempts left
    if otp_data["attempts_left"] <= 0:
        otp_storage.pop(email)
        return jsonify({"error": "Maximum attempts reached. Request a new OTP."}), 400

    # Verify OTP
    print(otp_data["otp"])
    if otp_data["otp"] == user_otp:
        otp_storage.pop(email)  # Remove OTP after successful verification
        return jsonify({"message": "OTP verified successfully!"}), 200
    else:
        otp_storage[email]["attempts_left"] -= 1  # Reduce attempt count
        return jsonify({"error": "Incorrect OTP. Attempts left: {}".format(otp_storage[email]["attempts_left"])}), 400

if __name__ == '__main__':
    app.run(debug=True)
