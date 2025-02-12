import os
import uuid
import random
import time
import smtplib
import jwt
import redis
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from email.message import EmailMessage

# Load environment variables from a .env file.
load_dotenv()

# Environment variables (ensure these are set in your .env file)
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MY_GMAIL = os.getenv("MY_GMAIL")
SIGNING_JWT_SECRET = os.getenv("SIGNING_JWT_SECRET")  # Secret key used for signing JWTs

# Optional Redis configuration (defaulting to localhost)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# SMTP configuration for Gmail.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Initialize Flask app.
app = Flask(__name__)

# Create a Redis client (frontend cannot access Redis if it’s not exposed publicly).
redis_client = redis.StrictRedis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)

#############################
# Helper Functions
#############################

def send_email(recipient, subject, content):
    """
    Sends an email using Gmail SMTP.
    """
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg["Subject"] = subject
        msg["From"] = MY_GMAIL
        msg["To"] = recipient

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(MY_GMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email sending error:", e)
        return False

def generate_otp():
    """
    Generate a random 6-digit OTP.
    """
    return str(random.randint(100000, 999999))

#############################
# Endpoint: /send_otp
#############################

@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Generate OTP details.
    otp = generate_otp()
    otp_id = str(uuid.uuid4())          # Unique identifier for this OTP request.
    start_time = time.time()              # Current timestamp.
    attempts_left = 5                     # Maximum number of attempts.

    # Create a data dictionary to store in Redis.
    otp_data = {
        "otp": otp,
        "start_time": start_time,
        "attempts_left": attempts_left
    }
    redis_key = f"otp:{otp_id}"
    redis_client.hmset(redis_key, otp_data)
    redis_client.expire(redis_key, 300)  # Set key to expire in 5 minutes (300 seconds).

    # Send the OTP to the user's email.
    email_sent = send_email(email, "Your OTP Code", f"Your OTP is: {otp}")
    if not email_sent:
        return jsonify({"error": "Failed to send OTP email"}), 500

    # Create the payload to be signed (exclude the OTP itself).
    payload = {
        "otp_id": otp_id,
        "start_time": start_time,
        "attempts_left": attempts_left
    }
    # Sign the payload using JWT.
    signed_payload = jwt.encode(payload, SIGNING_JWT_SECRET, algorithm="HS256")
    # (PyJWT v2+ returns a string; for earlier versions you might need to decode bytes.)
    if isinstance(signed_payload, bytes):
        signed_payload = signed_payload.decode("utf-8")

    # Return the signed payload to the frontend.
    return jsonify({
        "message": "OTP sent successfully",
        "signed_payload": signed_payload
    }), 200

#############################
# Endpoint: /verify_otp
#############################

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get("email")
    user_otp = data.get("otp")
    signed_payload = data.get("signed_payload")

    if not email or not user_otp or not signed_payload:
        return jsonify({"error": "Email, OTP, and signed payload are required"}), 400

    # Verify and decode the signed payload.
    try:
        payload = jwt.decode(signed_payload, SIGNING_JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Signed payload has expired"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid signed payload"}), 400
    
    otp_id = payload.get("otp_id")
    if not otp_id:
        return jsonify({"error": "Invalid signed payload data"}), 400

    redis_key = f"otp:{otp_id}"
    stored_data = redis_client.hgetall(redis_key)
    if not stored_data:
        return jsonify({"error": "OTP data not found or expired"}), 400

    # Check the expiration manually (Redis key expiry should cover this, but we add an extra check).
    stored_start_time = float(stored_data.get("start_time", 0))
    if time.time() > stored_start_time + 300:
        redis_client.delete(redis_key)
        return jsonify({"error": "OTP has expired"}), 400

    # Check remaining attempts.
    attempts_left = int(stored_data.get("attempts_left", 0))
    if attempts_left <= 0:
        redis_client.delete(redis_key)
        return jsonify({"error": "Maximum attempts reached"}), 400

    stored_otp = stored_data.get("otp")
    if stored_otp == user_otp:
        # Successful verification.
        redis_client.delete(redis_key)
        return jsonify({"message": "OTP verified successfully"}), 200
    else:
        # Decrement the remaining attempts.
        attempts_left -= 1
        redis_client.hset(redis_key, "attempts_left", attempts_left)
        return jsonify({"error": f"Incorrect OTP. Attempts left: {attempts_left}"}), 400

#############################
# Run the Flask Application
#############################

if __name__ == '__main__':
    app.run(debug=True)
