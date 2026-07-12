import pandas as pd

def generate_csv():
    data = [
        {"manifest_id": 1, "location_name": "Sydney_Office", "waste_type": "Recycling", "weight_kg": 150.5, "disposal_cert_url": "s3://certs/recycling_nov2025.pdf"},
        {"manifest_id": 2, "location_name": "Sydney_Office", "waste_type": "Hazardous", "weight_kg": 45.0, "disposal_cert_url": "s3://certs/hazard_nov2025.pdf"}
    ]
    
    file_name = "fact_waste_manifest.csv"
    pd.DataFrame(data).to_csv(file_name, index=False)
    print(f"SUCCESS: Generated {file_name} in current directory.")

if __name__ == "__main__":
    generate_csv()