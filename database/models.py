from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class User(db.Model):
    """User's table which stores uuid and email"""

    user_uuid = db.Column(db.String(256), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Document(db.Model):
    """Document table which stores the file metadata"""
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Unique document ID
    user_uuid = db.Column(db.String(256), db.ForeignKey("user.user_uuid"), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
