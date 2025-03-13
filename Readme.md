# Secure Document Upload Service

## Overview
This project implements a secure document upload service that allows users to register and authenticate via OTP-based verification, upload documents using temporary links that expire after 15 minutes, and query an AI endpoint that returns only documents associated with the authenticated user. The solution features file scanning using the VirusTotal API, secure file storage (with S3 integration for file storage), and user-specific data isolation for future AI/ML integration using Gemini API and FAISS.

## Features
- **User Registration & Authentication:**  
  - OTP-based verification with Redis-managed OTPs (5-minute expiry, 5 attempts) and JWT token generation for stateless session management.
  - If multiple OTPs are generated, Redis automatically retains only the latest OTP.
  
- **Ephemeral Document Upload:**  
  - Generates a unique upload link (stored in Redis) that expires in 15 minutes.
  - Validates the link against the user's JWT identity and allowed file types before uploading.
  - Uploaded files are scanned with VirusTotal; if clean, the file is uploaded to AWS S3, its metadata stored in the database, and its vector chunks indexed in FAISS.
  
- **User-Specific AI Query Endpoint:**  
  - A chat endpoint that allows the user to query their documents (e.g., “what is my file name?”).
  - Only document chunks associated with the authenticated user (via metadata in FAISS) are retrieved and sent to the Gemini API for Retrieval-Augmented Generation (RAG).
  
- **Security:**  
  - JWT tokens are stored in HTTP‑only cookies to prevent XSS, while CSRF protection is enforced.
  - Robust error handling, strict input validation, and file type restrictions minimize potential vulnerabilities.

## Getting Started

### Prerequisites
- Python 3.8+
- pip (Python package installer)
- Redis Server (running locally)
- AWS S3 bucket credentials for file storage
- Gmail Account with an app password for SMTP
- VirusTotal API Key
- Gemini API Key (for the language model)  
- (Optional) FAISS and Langchain libraries for vector indexing

### Setup

1. **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2. **Create a Virtual Environment and Install Dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3. **Set Environment Variables:**

   Create a `.env` file in the project root with the following content:
    ```env
    DOMAIN=http://127.0.0.1
    PORT=5000
    SIGNING_JWT_SECRET=your_jwt_secret_here
    JWT_SECRET_KEY=your_jwt_secret_here
    SQLALCHEMY_DATABASE_URI=sqlite:///users.db
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    REDIS_HOST=localhost
    REDIS_PORT=6379
    SMTP_SERVER=smtp.gmail.com
    SMTP_PORT=587
    MY_GMAIL=your_gmail_account
    GMAIL_APP_PASSWORD=your_gmail_app_password
    VIRUS_TOTAL_API_KEY=your_virustotal_api_key
    GEMINI_API_KEY=your_gemini_api_key
    AWS_ACCESS_KEY=your_aws_access_key
    AWS_SECRET_KEY=your_aws_secret_key
    AWS_S3_BUCKET=your_s3_bucket_name
    UPLOAD_FOLDER=uploaded_files
    ```
   *Note: The project automatically creates the `uploaded_files` directory if it doesn't exist.*

4. **Run the Application:**
    ```bash
    python app.py
    ```
    The application will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Project Structure

- **database/**  
  - **`__init__.py`**: Initializes the SQLAlchemy database.
  - **`models.py`**: Defines the `User` and `Document` models for storing user details and file metadata.

- **routes/**  
  - **`auth.py`**: Handles user authentication, OTP generation/verification, and JWT token generation.
  - **`chat_routes.py`**: Provides the chat endpoint that returns user-specific document information.
  - **`file_upload.py`**: Manages ephemeral upload links, file uploads to AWS S3, file scanning using VirusTotal, and indexing file content into FAISS.

- **templates/**  
  - **`index.html`**: Landing page for user authentication (email input and OTP verification).
  - **`otp_verify.html`**: Form for OTP verification with hidden fields.
  - **`chat.html`**: Chat interface that integrates file upload and chat query functionality.

- **utils/**  
  - **`email_services.py`**: Contains functions to send emails via Gmail SMTP.
  - **`redis_services.py`**: Implements Redis functions for OTPs and ephemeral upload links.
  - **(Optional)**: Additional utility modules for vector store integration (e.g., with FAISS).

- **static/**  
  - **`style.css`**: CSS styles for the frontend.

- **app.py**  
  - The main Flask application that configures settings, initializes the database, registers blueprints, and starts the server.

- **Config.py**  
  - Contains configuration settings including environment variables for domain, port, secrets, database URI, Redis, SMTP, AWS, VirusTotal, Gemini API, and upload folder.

- **requirements.txt**  
  - Lists all Python dependencies required to run the project.

## Demo Video
[Watch the Demo Video](https://drive.google.com/file/d/1wDf3v0krBhBmOWpwL-wbCzMI6_Zfp04Z/view)

## Summary
This project demonstrates a secure, modular solution for document upload and AI query. It emphasizes robust session management using JWT tokens stored in HTTP‑only cookies, ephemeral upload links with Redis, file safety via VirusTotal scanning, and personalized data retrieval through a vector store (FAISS) integrated with the Gemini API for Retrieval-Augmented Generation (RAG). The design prioritizes security, data isolation, and scalability.

Thank you for reviewing my project. Please feel free to reach out with any questions or feedback.
