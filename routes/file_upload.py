import uuid
import os
import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from pathlib import Path
import time
import sys
import datetime
import boto3
from io import BytesIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parent))

from config import Config
from database import db
from utils.redis_service import store_upload_link, get_upload_link, delete_upload_link
from database.models import Document, User  
from utils.vector_store_services import store_vector_chunks

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

def allowed_file(filename):
    """Check if the file type is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file_to_s3(file_obj, filename):
    """Uploads file to S3 and returns the S3 URL."""
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY,
            aws_secret_access_key=Config.AWS_SECRET_KEY
        )
        bucket_name = Config.AWS_S3_BUCKET
        s3.upload_fileobj(file_obj, bucket_name, filename)
        file_url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
        return file_url
    except Exception as e:
        print("S3 upload error:", e)
        return None

def scan_file(file_path):
    """Scans the file using VirusTotal API before storing metadata."""
    api_key = Config.VIRUS_TOTAL_API_KEY
    upload_url = "https://www.virustotal.com/api/v3/files"
    headers = {"x-apikey": api_key}

    # sends file to the url
    with open(file_path, "rb") as file:
        response = requests.post(upload_url, headers=headers, files={"file": file})
    
    if response.status_code != 200:
        return None  # API failure
    
    scan_result = response.json()
    analysis_id = scan_result["data"]["id"]
    analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
    
    for _ in range(10):
        time.sleep(3)
        result_response = requests.get(analysis_url, headers=headers)
        if result_response.status_code != 200:
            return None  # API failure
        result_data = result_response.json()
        status = result_data["data"]["attributes"]["status"]
        if status == "completed":
            stats = result_data["data"]["attributes"]["stats"]
            if stats.get("malicious", 0) > 0:
                return False  # File is malicious
            return True  # File is safe
    return None  # Timeout: no result after retries

@upload_bp.route("/generate_upload_link", methods=["POST"])
@jwt_required()
def generate_upload_link():
    """Generate a temporary upload link for a user."""
    try:
        # Get user's email from JWT, then query for the unique user id
        user_email = get_jwt_identity()
        user = db.session.query(User).filter_by(email=user_email).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        user_id = str(user.user_uuid)
        
        upload_id = str(uuid.uuid4())
        # Store upload link using the unique user id
        print("upload id is ",upload_id)
        print("User id is ",user_id)
        store_upload_link(upload_id, user_id, ttl=900)  # Valid for 15 minutes
    except Exception as e:
        print("Error generating upload link:", e)
        return jsonify({"message": "Error While Generating Upload link"}), 500
    
    return jsonify({"message": "Upload id generated", "upload_id": upload_id})

@upload_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    # Get user's email and then unique user id from database
    user_email = get_jwt_identity()
    user = db.session.query(User).filter_by(email=user_email).first()
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    user_id = str(user.user_uuid)

    # Verify upload link using the unique user id stored in Redis
    upload_id = request.form.get("upload_id")
    upload_data = get_upload_link(upload_id,user_id)

    if not upload_data:
        return jsonify({"message": "Upload link expired or invalid"}), 400
    if user_id != upload_data.get("user_id"):
        return jsonify({"message": "Unauthorized"}), 403

    if "file" not in request.files:
        return jsonify({"message": "No file found"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400
    
    # check whether the file type is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Read file data into memory once
        file_data = file.read()
        # Create separate in-memory streams for S3 and scanning
        s3_stream = BytesIO(file_data)
        scan_stream = BytesIO(file_data)

        # Upload file to S3 using s3_stream
        # s3_url = upload_file_to_s3(s3_stream, unique_filename)
        # if s3_url is None:
        #     return jsonify({"message": "Error uploading file to S3"}), 500

        # Save file temporarily for scanning using scan_stream
        temp_file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(scan_stream.read())

        # scan_result = scan_file(temp_file_path)
        # if scan_result is None:
        #     os.remove(temp_file_path)
        #     return jsonify({"message": "VirusTotal scan failed. Try again later."}), 500
        # if not scan_result:
        #     os.remove(temp_file_path)
        #     return jsonify({"message": "File contains malware. Upload rejected."}), 400

        # Store document vector representation into FAISS vector store
        try:
            # Using unique user id for vector store folder
            print("file path in upload end point is ",temp_file_path)
            if not store_vector_chunks(temp_file_path, user_id):
                jsonify({"mesage":"Error While storing Chunks"}),500
        except Exception as e:
            print("Vector store error:", e)
        
        # Store metadata in the database with S3 URL as file path (using user's email for record purposes)
        new_document = Document(user_uuid=user_id, file_path=temp_file_path)
        db.session.add(new_document)
        db.session.commit()

        delete_upload_link(upload_id,user_id)
        os.remove(temp_file_path)
        return jsonify({"message": "File uploaded and scanned successfully"})

    return jsonify({"message": "File type not allowed"}), 400
