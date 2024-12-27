from google.cloud import storage
import os

def upload_to_gcs(local_folder, bucket_name, gcs_folder="teaching_materials/"):
    """
    Upload files from local folder to GCS bucket
    
    Args:
        local_folder (str): Path to local folder containing teaching materials
        bucket_name (str): Name of GCS bucket
        gcs_folder (str): Folder path in GCS bucket
    """
    print(f"Uploading files from {local_folder} to GCS bucket: {bucket_name}")
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    for root, dirs, files in os.walk(local_folder):
        for file in files:
            local_path = os.path.join(root, file)
            # Create GCS path (remove local folder prefix and add GCS folder prefix)
            relative_path = os.path.relpath(local_path, local_folder)
            gcs_path = os.path.join(gcs_folder, relative_path)
            
            blob = bucket.blob(gcs_path)
            try:
                blob.upload_from_filename(local_path)
                print(f"Uploaded: {local_path} -> {gcs_path}")
            except Exception as e:
                print(f"Error uploading {local_path}: {str(e)}")

def ensure_materials_in_gcs(local_folder, bucket_name):
    """
    Check if materials exist in GCS, upload if not found
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # Check if any files exist in the teaching_materials folder
    blobs = list(bucket.list_blobs(prefix="teaching_materials/"))
    
    if not blobs:
        print("No teaching materials found in GCS. Uploading from local folder...")
        upload_to_gcs(local_folder, bucket_name)
    else:
        print(f"Found {len(blobs)} files in GCS bucket")