from sentence_transformers import SentenceTransformer

def search_embeddings(query, collection, top_k=5):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_embedding = model.encode([query])
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    return results["documents"], results["metadatas"]