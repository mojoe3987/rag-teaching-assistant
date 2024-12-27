import os
import logging
from io import BytesIO
from flask import Flask, request, jsonify, render_template
from google.cloud import storage
from PyPDF2 import PdfReader
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

# Global variables for teaching material processing
collection = None
chunks = []

# Google Cloud Storage (GCS) bucket name
BUCKET_NAME = "teach-assist-materials"

# GCS Helper Functions
def process_files_gcs(bucket_name, prefix="teaching_materials/"):
    """Processes files from a Google Cloud Storage bucket."""
    logger.info(f"Processing files from GCS bucket: {bucket_name}")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    all_text = []
    for blob in blobs:
        try:
            logger.info(f"Processing file: {blob.name}")
            if blob.name.endswith('.pdf'):
                content = blob.download_as_bytes()
                pdf_file = BytesIO(content)
                reader = PdfReader(pdf_file)
                text = ""
                for page_num, page in enumerate(reader.pages):
                    text += f"\n[Page {page_num + 1}]\n" + page.extract_text()
                all_text.append(text)
            else:
                logger.warning(f"Skipping non-PDF file: {blob.name}")
        except Exception as e:
            logger.error(f"Error processing {blob.name}: {str(e)}", exc_info=True)
    
    final_text = " ".join(all_text)
    return final_text

def upload_to_gcs(file, bucket_name, destination_blob_name):
    """Uploads a file to Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file)
    logger.info(f"Uploaded {destination_blob_name} to GCS bucket {bucket_name}")

# Flask Routes
@app.route("/", methods=["GET"])
def home():
    """Renders the home page."""
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    """Handles user questions."""
    global collection
    if not collection:
        return jsonify({"error": "Teaching materials not properly loaded."}), 500

    data = request.get_json() or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query cannot be empty."}), 400

    try:
        documents, metadatas = search_embeddings(query, collection)
        prompt = format_prompt(documents, query)
        answer = generate_answer_with_gpt(prompt)
        return jsonify({"query": query, "answer": answer})
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload():
    """Handles file uploads."""
    global collection, chunks
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected for uploading."}), 400
    
    try:
        destination_blob_name = f"teaching_materials/{file.filename}"
        upload_to_gcs(file, BUCKET_NAME, destination_blob_name)

        # Reprocess teaching materials
        raw_text = process_files_gcs(BUCKET_NAME)
        raw_text = clean_text(raw_text)
        chunks = chunk_text(raw_text)
        embeddings = generate_embeddings(chunks)
        collection = store_embeddings(chunks, embeddings)

        return jsonify({"message": f"File {file.filename} uploaded and processed successfully."})
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Initialize teaching materials during startup
try:
    logger.info("Loading teaching materials from GCS...")
    raw_text = process_files_gcs(BUCKET_NAME)
    raw_text = clean_text(raw_text)
    if raw_text.strip():
        chunks = chunk_text(raw_text)
        embeddings = generate_embeddings(chunks)
        collection = store_embeddings(chunks, embeddings)
        logger.info("Teaching materials loaded and processed successfully.")
    else:
        logger.warning("No content found in the teaching materials.")
except Exception as e:
    logger.error(f"Error initializing teaching materials: {str(e)}", exc_info=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)