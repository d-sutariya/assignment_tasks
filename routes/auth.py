import random
import jwt
from flask import Blueprint, request, jsonify
import time

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parents[1]))

# user defined modules
from database.models import db, User
from utils.redis_service import store_otp, get_otp, delete_otp,update_otp_attempts
from utils.email_service import send_email
from config import Config

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/send_otp", methods=["POST"])
def send_otp():
    """Generate and send OTP"""
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"message": "Email is required"}), 400

    otp = str(random.randint(100000, 999999))
    store_otp(email, otp)

    send_email(email, otp)

    signed_data = jwt.encode({"email": email, "timestamp": int(time.time())}, Config.SIGNING_JWT_SECRET, algorithm="HS256")
    
    return jsonify({"message": "OTP sent successfully", "signed_data": signed_data})

@auth_bp.route("/verify_otp", methods=["POST"])
def verify_otp():
    """Verify OTP"""
    data = request.json
    # print(data)
    email = data.get("email")
    otp = data.get("otp")
    signed_data = data.get("signed_data")

    if not email or not otp or not signed_data:
        return jsonify({"message": "Missing required fields"}), 400

    try:
        decoded_data = jwt.decode(signed_data, Config.SIGNING_JWT_SECRET, algorithms=["HS256"])
        if decoded_data["email"] != email:
            return jsonify({"message": "Invalid request"}), 400
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "OTP session expired"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid OTP session"}), 400

    stored_otp_data = get_otp(email)

    if not stored_otp_data:
        return jsonify({"message": "OTP expired or invalid"}), 400

    if stored_otp_data["otp"] != otp:
        attempts_left = int(stored_otp_data["attempts_left"]) - 1
        update_otp_attempts(email,attempts_left)
        if attempts_left <= 0:
            delete_otp(email)
            return jsonify({"message": "Too many failed attempts. Request a new OTP."}), 403
        else:
            print(attempts_left)
            return jsonify({"message": f"Invalid OTP attempts left: {attempts_left}"}), 400

    delete_otp(email)

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({"message": "Hello Existed User"})
    else:
        new_user = User(email=email)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Hello New User"})
