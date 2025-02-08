from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials
import requests
from dotenv import load_dotenv
import os

load_dotenv()
# Initialize Flask App
app = Flask(__name__)

# Load Firebase Admin SDK
cred = credentials.Certificate("private_keys/firebase_config.json")
firebase_admin.initialize_app(cred)

# Firebase API Key (Get from Firebase Console → Project Settings → General)
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

@app.route("/send_otp", methods=["POST"])
def send_otp():
    """Send OTP to user via Firebase"""
    phone_number = request.json.get("phone")

    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendVerificationCode?key={FIREBASE_API_KEY}"
    payload = {"phoneNumber": phone_number}

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        session_info = response.json().get("sessionInfo")
        return jsonify({"message": "OTP sent", "sessionInfo": session_info}), 200
    else:
        return jsonify({"error": response.json()}), 400

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    """Verify OTP entered by user"""
    session_info = request.json.get("sessionInfo")
    otp = request.json.get("otp")

    if not session_info or not otp:
        return jsonify({"error": "Invalid request"}), 400

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPhoneNumber?key={FIREBASE_API_KEY}"
    payload = {"sessionInfo": session_info, "code": otp}

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return jsonify({"message": "Valid message"}), 200
    else:
        return jsonify({"error": "Invalid OTP"}), 400

if __name__ == "__main__":
    app.run(debug=True)
