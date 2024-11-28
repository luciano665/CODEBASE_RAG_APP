from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
import os

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "codebase-app"

pc = Pinecone(api_key=PINECONE_API_KEY)

def store_embeddings(documents: list[Document]):
    """Store of embeddings as Vector DB into Pinecone

    Args:
        embeddings (list): List of embbedings with metadata 
    """
    
    embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    
    index = pc.Index(PINECONE_INDEX_NAME)
    vector_store = PineconeVectorStore.from_documents(
        documents=documents,
        embedding=embedding_function,
        index_name=index
    )
    return vector_store