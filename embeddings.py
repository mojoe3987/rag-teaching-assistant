from sentence_transformers import SentenceTransformer
import chromadb

def generate_embeddings(chunks, model_name="all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name)
    return model.encode(chunks)

def store_embeddings(chunks, embeddings, collection_name="teaching_materials"):
    client = chromadb.Client()
    collection = client.get_or_create_collection(name=collection_name)
    for i, chunk in enumerate(chunks):
        metadata = {"chunk_id": i, "chunk_length": len(chunk)}
        collection.add(
            documents=[chunk],
            metadatas=[metadata],
            ids=[str(i)],
            embeddings=[embeddings[i]]
        )
    return collection