import os
import logging
from io import BytesIO

from flask import Flask, request, jsonify, render_template
from google.cloud import storage
from PyPDF2 import PdfReader
import re

from ingestion import clean_text
from chunking import chunk_text
from embeddings import generate_embeddings, store_embeddings
from retrieval import search_embeddings
from generation import format_prompt, generate_answer_with_gpt

# Initialize Flask app
app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Cloud Storage (GCS) bucket name
BUCKET_NAME = "teach-assist-materials"

# Global variables for teaching material processing
collection = None
chunks = []

def parse_session_from_filename(filename):
    # Look for the word "session", optionally uppercase or lower,
    # possibly followed by spaces or an underscore, then digits
    match = re.search(r'[sS]ession[\s_]?(\d+)', filename)
    if match:
        return int(match.group(1))
    else:
        return "Unknown"

def process_pdf_pages(content: bytes, blob_name: str):
    """
    Return a list of (page_text, metadata) for each page in the PDF,
    injecting the 'Session X, Page Y' into the text as well.
    """
    docs = []
    try:
        pdf_file = BytesIO(content)
        reader = PdfReader(pdf_file)
        session_num = parse_session_from_filename(blob_name)  # e.g. "session_2.pdf" => 2

        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            
            # Hybrid approach: Put "Session X, Page Y: ..." in the text
            # so embeddings pick it up
            session_str = f"Session {session_num}, Page {page_idx}" if session_num else f"Page {page_idx}"
            combined_text = f"{session_str}\n{page_text}"

            # Also store structured metadata
            metadata = {
                "source_file": blob_name,
                "session": session_num,
                "page": page_idx
            }
            docs.append((combined_text, metadata))
    except Exception as e:
        logger.error(f"Error reading PDF content from {blob_name}: {str(e)}", exc_info=True)
    return docs

def process_files_gcs_with_metadata(bucket_name: str, prefix: str = "teaching_materials/"):
    """
    Gathers all files (PDFs, etc.) from GCS.
    Returns a list of (text, metadata) for each page or slide.
    """
    logger.info(f"Processing files from GCS bucket: {bucket_name}, prefix: {prefix}")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    all_docs = []
    for blob in blobs:
        filename = blob.name
        logger.info(f"Processing file: {filename}")
        try:
            if filename.lower().endswith('.pdf'):
                content = blob.download_as_bytes()
                pdf_pages = process_pdf_pages(content, filename)
                all_docs.extend(pdf_pages)
            else:
                logger.warning(f"Skipping non-PDF file: {filename}")
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
    
    return all_docs  # list of (text, metadata)

def upload_to_gcs(file, bucket_name: str, destination_blob_name: str) -> None:
    """
    Uploads a file to Google Cloud Storage.
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_file(file)
        logger.info(f"Uploaded {destination_blob_name} to GCS bucket {bucket_name}")
    except Exception as e:
        logger.error(f"Failed to upload {destination_blob_name}: {str(e)}", exc_info=True)
        raise e

def load_and_process_teaching_materials():
    """
    Loads docs from GCS, cleans them, chunks them, embeds them, stores them in the global collection.
    """
    global collection, chunks
    
    logger.info("Loading teaching materials from GCS...")
    docs_with_meta = process_files_gcs_with_metadata(BUCKET_NAME)
    
    if not docs_with_meta:
        logger.warning("No content found in the teaching materials.")
        return
    
    # Optional: clean each doc_text
    cleaned_docs = []
    for (doc_text, doc_meta) in docs_with_meta:
        # 'clean_text' is your function that cleans a single string
        cleaned = clean_text(doc_text)
        cleaned_docs.append((cleaned, doc_meta))
    
    chunked_docs = chunk_text(cleaned_docs)  # returns list of (chunk_text, chunk_meta)
    
    embeddings = generate_embeddings(chunked_docs)
    collection = store_embeddings(chunked_docs, embeddings)
    logger.info("Teaching materials loaded and processed successfully.")

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    global collection
    
    if not collection:
        return jsonify({"error": "Teaching materials not properly loaded."}), 500

    data = request.get_json() or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query cannot be empty."}), 400

    try:
        documents, metadatas = search_embeddings(query, collection)
        prompt = format_prompt(documents, metadatas, query)
        answer = generate_answer_with_gpt(prompt)
        
        # Return the final answer
        return jsonify({"query": query, "answer": answer})

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload():
    global collection, chunks
    
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected for uploading."}), 400
    
    try:
        destination_blob_name = f"teaching_materials/{file.filename}"
        upload_to_gcs(file, BUCKET_NAME, destination_blob_name)
        
        # Re-process teaching materials after upload
        load_and_process_teaching_materials()
        
        return jsonify({"message": f"File {file.filename} uploaded and processed successfully."})
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Initialize teaching materials on startup
try:
    load_and_process_teaching_materials()
except Exception as e:
    logger.error(f"Error initializing teaching materials: {str(e)}", exc_info=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
