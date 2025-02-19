from flask import Flask,render_template
from config import Config
from database import init_db
from routes.auth import auth_bp
from routes.file_upload import upload_bp
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database
init_db(app)
JWTManager(app)
# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(upload_bp)

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
