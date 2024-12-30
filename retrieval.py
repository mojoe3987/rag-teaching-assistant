from sentence_transformers import SentenceTransformer

def search_embeddings(query, collection, top_k=5):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_embedding = model.encode([query])
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    
    # Flatten the results for a single query:
    documents = results["documents"][0]    # ["chunk1_text", "chunk2_text", ...]
    metadatas = results["metadatas"][0]    # [{"session": 7, "page": 9}, {"session": ...}, ...]
    
    return documents, metadatas
