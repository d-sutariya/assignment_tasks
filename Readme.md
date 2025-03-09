# Secure Document Upload Service

## Overview
This project implements a secure document upload service that allows users to register/authenticate using OTP-based verification, upload documents via ephemeral links that expire after 15 minutes, and query a simulated AI endpoint that returns only the documents associated with the authenticated user. The solution includes file scanning using the VirusTotal API, secure file storage, and user-specific data isolation for potential future AI/ML integration.

## Features
- **User Registration & Authentication:**  
  OTP-based verification with JWT token generation for secure session management.
- **Ephemeral Document Upload:**  
  Unique upload links (stored in Redis) expire after 15 minutes, ensuring secure and temporary access for document uploads.
- **User-Specific AI Query Endpoint:**  
  A chat endpoint that, for demo purposes, returns the filenames of documents uploaded by the authenticated user.
- **File Security:**  
  Uploaded files are validated by type and scanned using the VirusTotal API before storage.
- **Modular Design:**  
  The project is organized using Flask Blueprints, SQLAlchemy for database operations, and Redis for ephemeral data storage.

## Getting Started

### Prerequisites
- **Python 3.8+**
- **pip** (Python package installer)
- **Redis Server** (running locally)
- **Gmail Account** with an app password enabled for SMTP
- **VirusTotal API Key**

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
  - **`__init__.py`**: Initializes the database using SQLAlchemy.  
  - **`models.py`**: Defines the database models (User and Document) for storing user details and document metadata.

- **routes/**  
  - **`auth.py`**: Handles user authentication, OTP generation, and verification, including JWT token generation.  
  - **`chat_routes.py`**: Provides the chat endpoint that returns filenames of documents uploaded by the authenticated user.  
  - **`file_upload.py`**: Manages ephemeral upload links, secure file uploads (with VirusTotal scanning), and saving document metadata.

- **templates/**  
  - **`index.html`**: The landing page for user authentication (OTP verification).  
  - **`chat.html`**: The chat interface that includes both a chat query box and file upload option, which is loaded after successful authentication.

- **utils/**  
  - **`email_services.py`**: Contains functions to send emails via Gmail SMTP.  
  - **`redis_services.py`**: Implements Redis-based storage for OTPs and ephemeral upload links.

- **app.py**  
  - The main Flask application that loads configurations, initializes the database, registers blueprints, and starts the server.

- **Config.py**  
  - Contains configuration settings including environment variables and other constants used throughout the project.

- **requirements.txt**  
  - Lists all Python dependencies required to run the project.

- **static/**  
  - **`style.css`**: Contains CSS styles for the front-end user interface.

- **Demo Video:**  
  https://drive.google.com/file/d/1wDf3v0krBhBmOWpwL-wbCzMI6_Zfp04Z/view

---

Thank you for reviewing my project. Please feel free to reach out with any questions or feedback.
