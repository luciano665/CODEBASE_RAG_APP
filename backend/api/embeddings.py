"""Emeddings detecting different languages using Tree-sitter
    -Hierarchical Metadata: association of methods with parent classes and capturing doctrings as part of chunkers
    - Token limits: splits over large chunks using text-based chunkers
    - More languages can be added in teh future
"""
from typing import List, Dict
from sentence_transformers import SentenceTransformer


def get_huggingface_embeddings(text: List[str], model_name="sentence-transformers/all-mpnet-base-v2"):
    """Generates the proper embeddings for the parsed chunks including the hierarchical order
        
    """
    
    model = SentenceTransformer(model_name)
        
    return model.encode(text, show_progress_bar=True)