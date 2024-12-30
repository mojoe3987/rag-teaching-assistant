# chunking.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_text(docs, chunk_size=200, chunk_overlap=100):
    """
    docs: list of (text, metadata)
    returns: list of (chunk_text, chunk_metadata)
    """
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    chunked_docs = []
    for (doc_text, doc_meta) in docs:
        # Split into chunks
        chunks = splitter.split_text(doc_text)
        
        # Build new metadata for each chunk
        for i, chunked_text in enumerate(chunks):
            chunk_meta = {
                **doc_meta,
                "chunk_index": i,
                "chunk_length": len(chunked_text)
            }
            chunked_docs.append((chunked_text, chunk_meta))
    
    return chunked_docs
