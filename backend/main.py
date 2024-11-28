"""Orchestration of the embedding process"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from api.github_clone import clone_repo
from api.chunking_parsing_AST import get_main_files_content
from api.embeddings import generate_embedding
from api.pineconestore import store_embeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

# Environment variables
CLONE_DIR = "./cloned_repos"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "codebase-app"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Dependency Initialization
try:
    embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = PineconeVectorStore.from_existing_index(
        index_name=PINECONE_INDEX_NAME,
        embedding=embedding_function
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    llm = ChatOpenAI(
        openai_api_key=GROQ_API_KEY,
        openai_proxy="https://api.groq.com/openai/v1"
    )
except Exception as e:
    logger.error(f"Error initializing dependencies: {e}")
    raise RuntimeError("Failed to initialize vector store or embeddings.")

# RAG Prompt
RAG_PROMPT = ChatPromptTemplate.from_template("""
Answer the user's query based strictly on the provided retrieved context:
{context}

Question: {question}
""")

# RAG Chain
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | RAG_PROMPT
    | llm
)

# Request Models
class RepoRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    query: str

@app.post("/submit-repo")
async def submit_repo(request: RepoRequest):
    """Process a repository."""
    try:
        clone_response = await clone_repo(request.repo_url)
        repo_path = clone_response.get("repo_path")
        if not repo_path:
            raise HTTPException(status_code=400, detail="Repository path not found.")

        parsed_chunks = get_main_files_content(repo_path)
        if not parsed_chunks:
            raise HTTPException(status_code=400, detail="No valid code files found.")

        embeddings = generate_embedding(parsed_chunks)
        store_embeddings(embeddings)

        return {"status": "success", "message": f"Repository processed: {repo_path}"}
    except HTTPException as http_exc:
        logger.error(f"HTTP Exception: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in submit_repo: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@app.post("/query")
async def query_codebase(request: QueryRequest):
    """Handle user queries."""
    try:
        result = rag_chain.invoke(request.query)
        return {"answer": result}
    except Exception as e:
        logger.error(f"Error in query_codebase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
