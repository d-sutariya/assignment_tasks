import uuid
import os
import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from werkzeug.utils import secure_filename
from datetime import datetime

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parents[1]))

from database import db
from utils.redis_service import store_upload_link, get_upload_link, delete_upload_link
from database.models import Document

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

def allowed_file(filename):
    """Check if the file type is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route("/generate_upload_link", methods=["POST"])
@jwt_required()
def generate_upload_link():
    """Generate a temporary upload link for a user."""
    user_email = get_jwt_identity()

    upload_id = str(uuid.uuid4())
    store_upload_link(upload_id, user_email, ttl=900)  # Valid for 15 minutes

    return jsonify({"message": "Upload link generated", "upload_id": upload_id})


import time
import requests

def scan_file(file_path):
    """Scans the file using VirusTotal API before saving it."""
    api_key = Config.VIRUS_TOTAL_API_KEY
    upload_url = "https://www.virustotal.com/api/v3/files"
    headers = {"x-apikey": api_key}

    # Step 1: Upload file to VirusTotal
    with open(file_path, "rb") as file:
        response = requests.post(upload_url, headers=headers, files={"file": file})
    
    if response.status_code != 200:
        return None  # API failure
    
    scan_result = response.json()
    analysis_id = scan_result["data"]["id"]  # Extract analysis ID

    # Step 2: Poll the results
    analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
    
    for _ in range(10):  # Retry for some time before giving up
        time.sleep(5)  # Wait before checking results
        result_response = requests.get(analysis_url, headers=headers)
        
        if result_response.status_code != 200:
            return None  # API failure

        result_data = result_response.json()
        status = result_data["data"]["attributes"]["status"]

        if status == "completed":
            # Step 3: Check if the file is malicious
            stats = result_data["data"]["attributes"]["stats"]
            if stats.get("malicious", 0) > 0:
                return False  # File is malicious
            return True  # File is safe
    
    return None  # Timeout: No result after retries


@upload_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    # Verify upload link
    upload_id = request.form.get("upload_id")  
    upload_data = get_upload_link(upload_id)
    if not upload_data:
        return jsonify({"message": "Upload link expired or invalid"}), 400

    user_email = get_jwt_identity()

    if not user_email or user_email != upload_data["email"]:
        return jsonify({"message": "Unauthorized"}), 403

    if "file" not in request.files:
        return jsonify({"message": "No file found"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        file.save(file_path)

        # **Scan file before storing metadata**
        scan_result = scan_file(file_path)

        if scan_result is None:
            os.remove(file_path)  # Remove file if VirusTotal API failed
            return jsonify({"message": "VirusTotal scan failed. Try again later."}), 500

        if not scan_result:
            os.remove(file_path)  # Remove malicious file
            return jsonify({"message": "File contains malware. Upload rejected."}), 400

        # **Store metadata if the file is clean**
        new_document = Document(user_email=user_email, filename=filename, file_path=file_path)
        db.session.add(new_document)
        db.session.commit()

        delete_upload_link(upload_id)  # Remove upload link after successful upload
        return jsonify({"message": "File uploaded and scanned successfully", "file_path": file_path})

    return jsonify({"message": "File type not allowed"}), 400




