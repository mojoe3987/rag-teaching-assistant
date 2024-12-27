from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_text(content, chunk_size=200, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(content)