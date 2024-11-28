import os
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_KEY = "codebase-app"

pc = Pinecone(api_key=PINECONE_API_KEY)

pinecone_index = pc.Index(PINECONE_INDEX_KEY)

#Embedding model initilaize globally
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

def store_embeddings(documents, namespace="default-name"):
    """Store documents and embeddings in Pincone V-DB"""
    vector_store = PineconeVectorStore.from_documents(
        documents=documents,
        embedding=embedding_model,
        index_name=PINECONE_INDEX_KEY,
        namespace=namespace
    )
    
    return vector_store