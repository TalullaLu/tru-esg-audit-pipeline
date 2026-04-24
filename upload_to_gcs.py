import os
from google.cloud import storage

def upload_to_bronze():
    # Explicitly set the Project ID to bypass credential discovery issues
    PROJECT_ID = "6605fdf2-1646-491b-800"
    BUCKET_NAME = "tru-esg-data-talul"
    
    client = storage.Client(project=PROJECT_ID)
    
    source_file = "raw_sensor_data_202411.csv"
    destination_blob = "bronze/raw_sensor_data_202411.csv"
    
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_blob)
    
    print(f"Uploading {source_file}...")
    blob.upload_from_filename(source_file)
    print("Success: File is now in the cloud.")

if __name__ == "__main__":
    upload_to_bronze()