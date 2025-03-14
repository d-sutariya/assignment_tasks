import uuid
import jwt
import random
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, make_response
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
        
        # Generate temporary JWT Token (valid for 5 minutes)
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        token_payload = {"sub": email, "exp": expiration_time}
        signed_data = jwt.encode(token_payload, Config.SIGNING_JWT_SECRET, algorithm="HS256")
        
        # Render OTP verification page and set temporary token as an HTTP-only cookie
        response = make_response(render_template("otp_verify.html",message="OTP sent successfully"))
        response.set_cookie("temp_token", signed_data, httponly=True, secure=False, samesite="Lax")
        return response
    
    return render_template("index.html")

@auth_bp.route("/verify_otp", methods=["POST"])
def verify_otp():
    # Read the OTP from 
    otp = request.form.get("otp")
    
    # Retrieve the temporary JWT from the HTTP-only cookie
    temp_token = request.cookies.get("temp_token")
    if not otp or not temp_token:
        return render_template("otp_verify.html", error="Missing OTP or token.")
    
    try:
        # Decode the temporary token to extract the user's email
        decoded_data = jwt.decode(temp_token, Config.SIGNING_JWT_SECRET, algorithms=["HS256"])
        email = decoded_data.get("sub")
        if not email:
            return render_template("otp_verify.html", error="Token missing user identifier.")
    except jwt.ExpiredSignatureError:
        return render_template("otp_verify.html", error="OTP session expired.")
    except jwt.InvalidTokenError:
        return render_template("otp_verify.html", error="Invalid OTP session.")
    
    # Retrieve the stored OTP data for the user from Redis
    stored_otp_data = get_otp(email)
    if not stored_otp_data:
        return render_template("otp_verify.html", error="OTP expired or invalid.")
    
    # Verify the OTP
    if stored_otp_data["otp"] != otp:
        attempts_left = int(stored_otp_data["attempts_left"]) - 1
        update_otp_attempts(email, attempts_left)
        if attempts_left <= 0:
            delete_otp(email)
            return render_template("index.html", error="Too many failed attempts. Request a new OTP.")
        else:
            return render_template("otp_verify.html", error=f"Invalid OTP. Attempts left: {attempts_left}")
    
    # OTP is verified; remove it from Redis
    delete_otp(email)
    
    # Retrieve or create the user in the database (with a unique user UUID)
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, user_uuid=str(uuid.uuid4()))
        db.session.add(user)
        db.session.commit()
    
    # Generate a permanent JWT Token (valid for 2 hours)
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    token_payload = {"sub": email, "exp": expiration_time}
    jwt_token = jwt.encode(token_payload, Config.SIGNING_JWT_SECRET, algorithm="HS256")
    
    # Set the permanent JWT as an HTTP-only cookie and redirect to the chat page
    response = redirect(url_for("chat.chat_page"))
    response.set_cookie("access_token", jwt_token, httponly=True, secure=False, samesite="Lax")

    # Clear the temporary token cookie
    response.set_cookie("temp_token", "", expires=0)
    
    return response

