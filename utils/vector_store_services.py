import os
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from config import Config

def store_vector_chunks(filepath, user_uuid):
    """
    Loads file content from 'filepath', splits it into chunks, attaches the user's uuid as metadata,
    indexes the chunks into a FAISS vector store using Google Generative AI Embeddings,
    and saves the vector store locally in a folder unique to the user.
    """
    try:
        # Load document(s) from the file
        loader = TextLoader(filepath)
        docs = loader.load()  

        # Use a character splitter for chunking
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = []
        
        for doc in docs:
            text_chunks = splitter.split_text(doc.page_content)
            for chunk in text_chunks:
                chunks.append(Document(page_content=chunk, metadata={"user_uuid": user_uuid}))

        # Create the embedding model (Fixed model name)
        embedder = GoogleGenerativeAIEmbeddings(model = 'models/embedding-001',google_api_key=Config.GEMINI_API_KEY)

        # Build the FAISS vector store from document chunks
        vector_store = FAISS.from_documents(chunks, embedding=embedder)

        # Save the FAISS index locally
        save_dir = os.path.join("vector_store", f"{user_uuid}_index")
        os.makedirs(save_dir, exist_ok=True)
        vector_store.save_local(save_dir)
    except Exception as e:
        print(e)

