import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    DOMAIN = "http://127.0.0.1"
    PORT = 5000
    SQLALCHEMY_DATABASE_URI = "sqlite:///users.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    GMAIL_USER = os.getenv("MY_GMAIL")
    GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
    VIRUS_TOTAL_API_KEY = os.getenv("VIRUS_TOTAL_API_KEY")
    UPLOAD_FOLDER = os.path.join("uploaded_files")
    GEMINI_API_KEY= os.getenv("GEMINI_API_KEY")
    SIGNING_JWT_SECRET = os.getenv("SIGNING_JWT_SECRET")
    JWT_SECRET_KEY = SIGNING_JWT_SECRET
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
    
    # Tell Flask-JWT-Extended to look for the token in cookies
    JWT_TOKEN_LOCATION = ["cookies"]

    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_COOKIE_NAME = "access_token"
    JWT_COOKIE_SECURE = False  # Set to True in production (requires HTTPS)
    JWT_COOKIE_SAMESITE = "Lax"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
