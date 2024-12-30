from sentence_transformers import SentenceTransformer
import chromadb

def generate_embeddings(chunked_docs, model_name="all-MiniLM-L6-v2"):
    """
    chunked_docs: list of (chunk_text, chunk_metadata)
    returns a list of embeddings, in the same order
    """
    model = SentenceTransformer(model_name)
    texts = [doc[0] for doc in chunked_docs]  # extract chunk_text only
    embeddings = model.encode(texts)
    return embeddings

def store_embeddings(chunked_docs, embeddings, collection_name="teaching_materials"):
    """
    chunked_docs: list of (chunk_text, chunk_metadata)
    embeddings: corresponding list of embeddings
    """
    client = chromadb.Client()
    collection = client.get_or_create_collection(name=collection_name)
    
    for i, (chunk_text, chunk_meta) in enumerate(chunked_docs):
        # Ensure metadata has no None values:
        safe_meta = remove_none_fields(chunk_meta)
        
        collection.add(
            documents=[chunk_text],
            metadatas=[safe_meta],  # store slide/page/session safely
            ids=[f"{collection_name}_{i}"],
            embeddings=[embeddings[i]]
        )
    return collection

def remove_none_fields(meta_dict):
    """
    Recursively remove or convert None values from metadata
    so Chroma doesn't throw an error.
    """
    clean_dict = {}
    for key, value in meta_dict.items():
        if value is None:
            # Option A: skip this key entirely
            # continue

            # Option B: convert None to a valid string:
            clean_dict[key] = "Unknown"
        else:
            clean_dict[key] = value
    return clean_dict
