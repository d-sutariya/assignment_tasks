from flask import Flask
from database.models import db

def init_db(app: Flask):
    db.init_app(app)
    with app.app_context():
        db.create_all()
