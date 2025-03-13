import uuid
import os
import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from pathlib import Path
import time
import sys
import boto3
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from io import BytesIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parent))

from config import Config
from database import db
from utils.redis_service import store_upload_link, get_upload_link, delete_upload_link
from database.models import Document
from vector_store_services import store_vector_chunks

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
        user_email = get_jwt_identity()
        upload_id = str(uuid.uuid4())
        store_upload_link(upload_id, user_email, ttl=900)  # Valid for 15 minutes
    except Exception as e:
        return jsonify({"message": "Error While Generating Upload link"}), 500
    return jsonify({"message": "Upload link generated", "upload_id": upload_id})

@upload_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    # Verify upload link
    upload_id = request.form.get("upload_id")
    upload_data = get_upload_link(upload_id)
    if not upload_data:
        return jsonify({"message": "Upload link expired or invalid"}), 400

    user_email = get_jwt_identity()
    if not user_email or user_email != upload_data.get("email"):
        return jsonify({"message": "Unauthorized"}), 403

    if "file" not in request.files:
        return jsonify({"message": "No file found"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Read file data into memory once
        file_data = file.read()
        # Create separate in-memory streams for S3 and scanning
        s3_stream = BytesIO(file_data)
        scan_stream = BytesIO(file_data)

        # Upload file to S3 using s3_stream
        s3_url = upload_file_to_s3(s3_stream, unique_filename)
        if s3_url is None:
            return jsonify({"message": "Error uploading file to S3"}), 500

        # Save file temporarily for scanning using scan_stream
        temp_file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(scan_stream.read())

        scan_result = scan_file(temp_file_path)
        if scan_result is None:
            os.remove(temp_file_path)
            return jsonify({"message": "VirusTotal scan failed. Try again later."}), 500
        if not scan_result:
            os.remove(temp_file_path)
            return jsonify({"message": "File contains malware. Upload rejected."}), 400

        # Store vector representation into FAISS vector store
        try:
            store_vector_chunks(temp_file_path, user_email)
        except Exception as e:
            print("Vector store error:", e)
        
        # Store metadata in database with S3 URL as file path
        new_document = Document(user_email=user_email, filename=filename, file_path=s3_url)
        db.session.add(new_document)
        db.session.commit()

        delete_upload_link(upload_id)
        os.remove(temp_file_path)
        return jsonify({"message": "File uploaded and scanned successfully", "file_path": s3_url})

    return jsonify({"message": "File type not allowed"}), 400
