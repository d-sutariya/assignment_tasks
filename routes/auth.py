from flask import Blueprint, request, jsonify, url_for, redirect, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
import jwt
import random
import time
import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parents[1]))

from database.models import db, User
from utils.redis_service import store_otp, get_otp, delete_otp, update_otp_attempts
from utils.email_service import send_email
from config import Config

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/send_otp", methods=["GET", "POST"])
def send_otp():
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            return render_template("index.html", error="Email is required")
    
        otp = str(random.randint(100000, 999999))
        store_otp(email, otp)
    
        response = send_email(email, otp)
        if not response:
            return render_template("index.html", error="Internal Server Error")
            
        signed_data = jwt.encode(
            {"email": email, "timestamp": int(time.time())},
            Config.SIGNING_JWT_SECRET,
            algorithm="HS256"
        )
        
        # Render the OTP verification page with hidden fields for email and signed_data
        return render_template("otp_verify.html", email=email, signed_data=signed_data, message="OTP sent successfully")
    return render_template("index.html")


@auth_bp.route("/verify_otp", methods=["POST"])
def verify_otp():
    email = request.form.get("email")
    otp = request.form.get("otp")
    signed_data = request.form.get("signed_data")
    
    if not email or not otp or not signed_data:
        return render_template("otp_verify.html", error="Missing required fields", email=email, signed_data=signed_data)
    
    try:
        decoded_data = jwt.decode(signed_data, Config.SIGNING_JWT_SECRET, algorithms=["HS256"])
        if decoded_data["email"] != email:
            return render_template("otp_verify.html", error="Invalid request", email=email, signed_data=signed_data)
    except jwt.ExpiredSignatureError:
        return render_template("otp_verify.html", error="OTP session expired", email=email, signed_data=signed_data)
    except jwt.InvalidTokenError:
        return render_template("otp_verify.html", error="Invalid OTP session", email=email, signed_data=signed_data)
    
    stored_otp_data = get_otp(email)
    if not stored_otp_data:
        return render_template("otp_verify.html", error="OTP expired or invalid", email=email, signed_data=signed_data)
    
    if stored_otp_data["otp"] != otp:
        attempts_left = int(stored_otp_data["attempts_left"]) - 1
        update_otp_attempts(email, attempts_left)
        if attempts_left <= 0:
            delete_otp(email)
            return render_template("index.html", error="Too many failed attempts. Request a new OTP.")
        else:
            return render_template("otp_verify.html", error=f"Invalid OTP. Attempts left: {attempts_left}", email=email, signed_data=signed_data)
    
    delete_otp(email)
    
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    
    # Generate JWT Token (valid for 2 hours)
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    token_payload = {"sub": email, "exp": expiration_time}
    jwt_token = jwt.encode(token_payload, Config.SIGNING_JWT_SECRET, algorithm="HS256")
    
    # Set the JWT as an HTTP-only cookie and redirect to chat page
    response = redirect(url_for("chat.chat_page"))
    response.set_cookie("access_token", jwt_token, httponly=True, secure=False, samesite="Lax")
    return response
