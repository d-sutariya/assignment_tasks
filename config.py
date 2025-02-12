import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    SIGNING_JWT_SECRET = os.getenv("SIGNING_JWT_SECRET")
    SQLALCHEMY_DATABASE_URI = "sqlite:///users.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    GMAIL_USER = os.getenv("MY_GMAIL")
    GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
