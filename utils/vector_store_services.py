import os
from langchain_community.document_loaders import TextLoader,PyMuPDFLoader
from langchain.text_splitter import CharacterTextSplitter,RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain.schema import Document as LC_Document  # Use LangChain's Document type
from config import Config
import time
import re

def post_processing(chunks):
    updated_chunks=[]
    for text in chunks:
        text = re.sub(r'\s+',' ',text)
        text.replace("\n","")
        updated_chunks.append(text)
    return updated_chunks

def store_vector_chunks(filepath:str, user_uuid:str):
    """
    Loads file content from 'filepath', splits it into chunks, attaches the user's uuid as metadata,
    indexes the chunks into a FAISS vector store using Google Generative AI Embeddings,
    and saves (or updates) the vector store locally in a folder unique to the user.
    """

    try:
        # Load document(s) from the file.
        if filepath.split(".")[1] == "pdf":
            loader = PyMuPDFLoader(filepath)
        if filepath.split(".")[1] == "txt":
            loader = TextLoader(file_path=filepath)
        docs = loader.load()  # List of Document objects with a 'page_content' attribute
        # print("Time taken is ", time.time()-start_time)
        # Use a character splitter for chunking.
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=100,
            separators=["\n\n","\n","."," "]
        )
        new_chunks = []
        
        for doc in docs:
            text_chunks = splitter.split_text(doc.page_content)
            text_chunks = post_processing(text_chunks)
            for chunk in text_chunks:
                new_chunks.append(LC_Document(page_content=chunk, metadata={"user_uuid": user_uuid}))

        # Create the embedding model with the correct model name.
        embedder = GoogleGenerativeAIEmbeddings(
            google_api_key=Config.GEMINI_API_KEY,
            model="models/embedding-001"
        )

        # Define the FAISS index path for the user.
        save_dir = os.path.join("vector_store", f"{user_uuid}_index")
        os.makedirs(save_dir, exist_ok=True)
        
        # If the index exists (i.e. the folder is not empty), load it; otherwise, create a new one.
        try:
            if os.listdir(save_dir):
                vector_store = FAISS.load_local(save_dir, embedder,allow_dangerous_deserialization=True)
                vector_store.add_documents(new_chunks)
            else:
                vector_store = FAISS.from_documents(new_chunks, embedding=embedder)
        except Exception as e:
            print(e)
            return False
        # Save (or update) the FAISS vector store locally.
        vector_store.save_local(save_dir)
    except Exception as e:
        print("Error in store_vector_chunks:", e)
        return False
    
    return True


