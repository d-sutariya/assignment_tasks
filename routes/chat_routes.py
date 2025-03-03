from flask import Blueprint, request, jsonify,render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import db, Document
import jwt
from config import Config

chat_bp = Blueprint("chat", __name__)   

@chat_bp.route("/chat_page", methods=["GET"])
def chat_page():
    token = request.args.get("token")
    if not token:
        return jsonify({"message": "Missing token"}), 400
    try:
        decoded_data = jwt.decode(token, Config.SIGNING_JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Session expired"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 400
   
    return render_template("chat.html", token=token)


@chat_bp.route("/chat", methods=["POST"])
@jwt_required()
def user_query():
    """Returns the filenames of documents uploaded by the authenticated user."""
    user_email = get_jwt_identity()
    user_query = request.json.get("query")

    documents = Document.query.filter_by(user_email=user_email).all()

    if not documents:
        return jsonify({"response": "You have not uploaded any files."})

    file_names = [f"{doc.filename}\n" for doc in documents]
    return jsonify({"response": file_names})
