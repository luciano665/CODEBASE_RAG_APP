# CODEBASE RAG APP

**CODEBASE RAG APP** is an AI-powered tool for interacting with codebases dynamically. It leverages advanced chunking, parsing, and embedding techniques to enable efficient exploration and understanding of large repositories.

## Features

- **Clone Repositories**: Clone GitHub repositories directly for analysis.
- **Tree-sitter Parsing**: Extract meaningful code components (e.g., classes, methods, comments) using AST techniques.
- **Embeddings**: Generate embeddings using Hugging Face models.
- **Pinecone Integration**: Store and retrieve vector embeddings for scalable, fast queries.
- **End-to-End Functionality**: Supports seamless processing, from cloning repositories to querying insights.

---

## Installation and Usage

### Prerequisites

Ensure you have the following installed:
- Python 3.8+
- Pinecone API Key
- Git

### Setup

1. **Clone the Repository**:
   ```
   git clone <repository_url>
   cd CODEBASE_RAG_APP-main
   ```
2. **Install Dependencies:
- Install the required Python packages:
  ```  
  pip install -r requirements.txt
  ```
3. **Set Up Kesy: Create a .env file in the project directory and add your Pinecone API key and GROQ api:
  ```
  PINECONE_API_KEY=<your_pinecone_api_key>
  GROQ_API_KEY=<your_key>
  ```
    - Make sure to also crete your own Pinecone-Index

5. **Run the API first:
   ```
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. Run the Application: 
  ```
  python main.py
  ```

