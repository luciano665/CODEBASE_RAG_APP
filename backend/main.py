import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from api.chunking_parsing_AST import parse_repo_store_all
from api.embeddings import get_huggingface_embeddings
from api.pinecone_interactions import store_embeddings, embedding_model, pinecone_index
from git import Repo
from langchain.schema import Document
from dotenv import load_dotenv
import openai  # Using OpenAI client for simplified RAG
import numpy as np

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Environment variables
PINECONE_INDEX_KEY = "codebase-app"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CLONE_DIR = "./cloned_repos"

# Initialize OpenAI client
client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

# Initialize Pinecone

# Models
class RepoRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    query: str

# GitHub Cloning
def clone_repository(repo_url: str) -> str:
    """
    Clone a GitHub repository to the local directory.
    """
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(CLONE_DIR, repo_name)
    try:
        if not os.path.exists(CLONE_DIR):
            os.makedirs(CLONE_DIR)
        if os.path.exists(repo_path):
            logger.info(f"Repository already exists: {repo_path}")
            return repo_path
        Repo.clone_from(repo_url, repo_path)
        logger.info(f"Cloned repository to: {repo_path}")
        return repo_path
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise HTTPException(status_code=500, detail="Failed to clone repository.")

# Simplified RAG Process
def perform_rag(query: str, namespace="default") -> str:
    """
    Perform Retrieval-Augmented Generation (RAG) for the given query.
    """
    logger.info(f"Performing RAG for query: {query} in namespace: {namespace}")

    # Retrieve top documents from Pinecone
     # Retrieve top documents from Pinecone
    raw_query_embedding = embedding_model.embed_query(query)
    if isinstance(raw_query_embedding, list):  # If already a list, no need to convert
        vector = raw_query_embedding
    else:  # If not a list, ensure it's converted to a list
        vector = raw_query_embedding.tolist()

    response = pinecone_index.query(
        vector=vector,
        top_k=10,
        include_metadata=True,
        namespace=namespace
    )
    logger.info(f"Retrieved {len(response['matches'])} documents from Pinecone.")
    # Check if any documents were retrieved
    if not response['matches']:
        logger.warning(f"No relevant documents found for namespace: {namespace}")
        return "No relevant context found for the query."

    # Format retrieved documents for LLM input
    contexts = [match['metadata'].get('text', '') for match in response['matches']]
    augmented_query = "<CONTEXT>\n" + "\n\n-------\n\n".join(contexts) + "\n-------\n</CONTEXT>\n\n\n\nMY QUESTION:\n" + query
    logger.info(f"Augmented query sent to LLM: {augmented_query}")

    # Create system prompt for LLM
    system_prompt = f"""You are a Senior Software Engineer, specializing in TypeScript.

    Answer any questions I have about the codebase, based on the code provided. Always consider all of the context provided when forming a response.
    """

    # Generate response from LLM
    llm_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": augmented_query}
        ]
    )

    return llm_response.choices[0].message.content

# API Endpoints
@app.post("/submit-repo")
async def submit_repo(request: RepoRequest):
    """
    Process a GitHub repository: clone, parse, generate embeddings, and store them.
    """
    namespace = request.repo_url.split("/")[-1].replace(".git", "")
    try:
        logger.info(f"Processing repository for namespace: {namespace}")

        # Clone repository
        repo_path = clone_repository(request.repo_url)

        # Parse repository and store both structured chunks and raw file content
        chunks = parse_repo_store_all(repo_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="No valid code chunks found in the repository.")

        # Generate embeddings
        embeddings = get_huggingface_embeddings([str(chunk) if isinstance(chunk, dict) else chunk for chunk in chunks])

        # Check if embeddings are valid
        if not isinstance(embeddings, (list, np.ndarray)) or len(embeddings) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate embeddings.")

        # Store embeddings in Pinecone
        documents = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                # Convert dictionary chunks to a string format
                content = str(chunk)
            else:
                # Use raw file content as-is
                content = chunk

            documents.append(
                Document(
                    page_content=content,
                    metadata={"repo_url": request.repo_url}
                )
            )

        store_embeddings(documents, namespace=namespace)

        return {"status": "success", "message": "Repository processed successfully."}

    except HTTPException as http_exc:
        logger.error(f"HTTP Exception: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in submit_repo: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
@app.post("/query")
async def query_codebase(request: QueryRequest):
    """
    Handle a user's query using the simplified RAG process.
    User can query from a specific namespace.
    """
    try:
        # Extract namespace and query from the input
        if "namespace=" in request.query:
            parts = request.query.split("namespace=")
            namespace_and_query = parts[1].strip()  # Get everything after 'namespace='
            namespace, *query_parts = namespace_and_query.split(maxsplit=1)
            query = query_parts[0] if query_parts else "What is this code about?"
        else:
            namespace = "default"
            query = request.query  # Assume the whole string is the query

        logger.info(f"Query received: {request.query}")
        logger.info(f"Using namespace: {namespace}")

        # Perform RAG with the extracted namespace and query
        answer = perform_rag(query, namespace=namespace)
        return {"answer": answer}

    except Exception as e:
        logger.error(f"Error in query_codebase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
