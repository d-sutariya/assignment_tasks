from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from config import Config
import os
from pathlib import Path

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat_page", methods=["GET"])
@jwt_required()
def chat_page():
    return render_template("chat.html")

@chat_bp.route("/chat", methods=["POST"])
@jwt_required()
def user_query():
    # Get the authenticated user's email
    user_email = get_jwt_identity()
    user_query_text = request.json.get("query")
    
    if not user_query_text:
        return jsonify({"response": "No query provided."}), 400

    # Construct the FAISS index path
    index_path = str(Path(__file__).parents[1] / 'vector_store' / f"{user_email}_index")
    index_path = os.path.abspath(index_path)

    # Check if the FAISS index folder and required files exist
    index_file = os.path.join(index_path, "index.faiss")
    metadata_file = os.path.join(index_path, "index.pkl")

    if not os.path.exists(index_path) or not os.listdir(index_path):
        return jsonify({"response": "No vector index found. Please upload documents first."}), 400

    if not os.path.exists(index_file) or not os.path.exists(metadata_file):
        return jsonify({"response": "FAISS index files missing. Please re-upload documents."}), 400

    # Initialize the embedding model
    embedder = GoogleGenerativeAIEmbeddings(
        google_api_key=Config.GEMINI_API_KEY,
        model="models/embedding-001"  # Corrected model name
    )
    
    try:
        vector_store = FAISS.load_local(index_path, embedder,allow_dangerous_deserialization=True)
    except Exception as e:
        return jsonify({"response": f"Error loading FAISS index: {str(e)}"}), 500

    # Perform a semantic similarity search
    retrieved_docs = vector_store.similarity_search(user_query_text)

    # Filter retrieved docs for the correct user
    filtered_docs = [doc for doc in retrieved_docs if doc.metadata.get("user_email") == user_email]
    
    if not filtered_docs:
        return jsonify({"response": "No relevant documents found for your query."})

    # Combine the content of the filtered documents
    context = " ".join([doc.page_content for doc in filtered_docs])
    # print(context)
    # Create a RAG prompt
    prompt = f"Query: {user_query_text}\nContext: {context}"
    
    # Call the Gemini API using ChatGoogleGenerativeAI
    chat_model = ChatGoogleGenerativeAI(model = "gemini-1.5-flash",google_api_key=Config.GEMINI_API_KEY)
    chat_response = chat_model.invoke(input=prompt).content
    
    return jsonify({"response": chat_response})

