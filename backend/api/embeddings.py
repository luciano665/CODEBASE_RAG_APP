"""Emeddings detecting different languages using Tree-sitter
    -Hierarchical Metadata: association of methods with parent classes and capturing doctrings as part of chunkers
    - Token limits: splits over large chunks using text-based chunkers
    - More languages can be added in teh future
"""
from typing import List, Dict
from sentence_transformers import SentenceTransformer


def generate_embedding(chunks: List[Dict]) -> List[dict]:
    """Generates the proper embeddings for the parsed chunks including the hierarchical order

    Args:
        chunks (List[Dict]): List of Parsed chuks

    Returns:
        List[dict]: Embeddings with metadata
    """
    
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    embeddings = []
    
    for chunk in chunks:
        # Generate embedding for the content of the chunk
        embedding = model.encode(chunk["content"], show_progress_bar=True)
        embeddings.append({
            "embedding": embedding,
            "metadata": {
                "type": chunk["type"],
                "name": chunk.get("name"),
                "path": chunk["path"],
                "start_line": chunk.get("start_line"),
                "end_line": chunk.get("end_line"),
            }
        })
    return embeddings