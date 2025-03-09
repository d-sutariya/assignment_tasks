from flask import Blueprint, render_template,jsonify,request
from flask_jwt_extended import jwt_required
from flask_jwt_extended import get_jwt_identity

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat_page", methods=["GET"])
@jwt_required()
def chat_page():
    # Render the chat interface; JWT is automatically provided from the cookie.
    return render_template("chat.html")

@chat_bp.route("/chat", methods=["POST"])
@jwt_required()
def user_query():
    
    user_email = get_jwt_identity()
    user_query = request.json.get("query")
    
    from database.models import Document
    documents = Document.query.filter_by(user_email=user_email).all()    

    if not documents:
        return jsonify({"response": "You have not uploaded any files."})

    file_names = [f"{doc.filename}\n" for doc in documents]
    return jsonify({"response": file_names})
