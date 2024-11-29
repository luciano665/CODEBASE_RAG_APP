import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.api.chunking_parsing_AST import parse_repo_store_all
from backend.api.embeddings import get_huggingface_embeddings
from backend.api.pinecone_interactions import store_embeddings, embedding_model, pinecone_index
from git import Repo
from langchain.schema import Document
from dotenv import load_dotenv
import openai
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

# Models
class RepoRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    query: str
    history: list
    namespace: str

# GitHub Cloning
def clone_repository(repo_url: str) -> str:
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
    logger.info(f"Performing RAG for query: {query} in namespace: {namespace}")
    raw_query_embedding = embedding_model.embed_query(query)
    vector = raw_query_embedding if isinstance(raw_query_embedding, list) else raw_query_embedding.tolist()
    logger.info(f"Embedding vector length: {len(vector)}")
    response = pinecone_index.query(
        vector=vector,
        top_k=10,
        include_metadata=True,
        namespace=namespace
    )
    logger.info(f"Pinecone query response: {response}")
    if not response['matches']:
        return "No relevant context found for the query."
    contexts = [match['metadata'].get('text', '') for match in response['matches']]
    augmented_query = "<CONTEXT>\n" + "\n\n-------\n\n".join(contexts) + "\n-------\n</CONTEXT>\n\n" + query
    llm_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Answer as concisely as possible."},
            {"role": "user", "content": augmented_query}
        ]
    )
    return llm_response.choices[0].message.content

# API Endpoints
@app.get("/namespaces")
async def list_namespaces():
    try:
        namespaces = pinecone_index.describe_index_stats().get("namespaces", {}).keys()
        return {"namespaces": list(namespaces)}
    except Exception as e:
        logger.error(f"Error fetching namespaces: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch namespaces.")

@app.post("/submit-repo")
async def submit_repo(request: RepoRequest):
    namespace = request.repo_url.split("/")[-1].replace(".git", "")
    try:
        repo_path = clone_repository(request.repo_url)
        chunks = parse_repo_store_all(repo_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="No valid code chunks found.")
        embeddings = get_huggingface_embeddings(chunks)
        documents = [
            Document(page_content=str(chunk), metadata={"repo_url": request.repo_url})
            for chunk in chunks
        ]
        store_embeddings(documents, namespace=namespace)
        return {"status": "success", "message": "Repository processed successfully."}
    except Exception as e:
        logger.error(f"Error in submit_repo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_codebase(request: QueryRequest):
    try:
        namespace = request.namespace
        query = request.query
        history_context = "\n".join([f"{entry['role']}: {entry['content']}" for entry in request.history])
        augmented_query = f"History:\n{history_context}\n\nQuery:\n{query}" if history_context else query
        answer = perform_rag(augmented_query, namespace=namespace)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error in query_codebase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
