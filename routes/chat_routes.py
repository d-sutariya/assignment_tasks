from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import Document
from langchain.vectorstores import FAISS
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from config import Config
import os

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

    # Load FAISS index
    index_path = os.path.join("vector_store")
    embedder = GoogleGenerativeAIEmbeddings(
        google_api_key=Config.GEMINI_API_KEY,
        model='model/embedding-001'
    )
    
    try:
        vector_store = FAISS.load_local(index_path, embedder)
    except Exception as e:
        return jsonify({"response": "No vector index found. Please upload documents first."}), 400

    # Perform a semantic similarity search on the vector store using the user's query.
    retrieved_docs = vector_store.similarity_search(user_query_text)
    
    # Filter the retrieved documents to include only those whose metadata's user_email matches.
    filtered_docs = [doc for doc in retrieved_docs if doc.metadata.get("user_email") == user_email]
    
    if not filtered_docs:
        return jsonify({"response": "No relevant documents found for your query."})

    # Combine the content of the filtered documents to form a context.
    context = " ".join([doc.page_content for doc in filtered_docs])
    
    # Create a prompt for the Gemini API using Retrieval-Augmented Generation (RAG).
    prompt = f"Query: {user_query_text}\nContext: {context}"
    
    # Call the Gemini API using the ChatGoogleGenerativeAI model.
    chat_model = ChatGoogleGenerativeAI(google_api_key=Config.GEMINI_API_KEY)
    chat_response = chat_model.generate(prompt=prompt)
    
    return jsonify({"response": chat_response})
