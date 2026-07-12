import pandas as pd

def generate_csv():
    data = [
        {"asset_id": "Asset_01_NZ_Boundary", "billing_month": "2025-11-01", "actual_billed_kwh": 5000.0, "inferred_kwh": 4950.0, "uploaded_pdf_hash": "hash_abc123", "original_crypto_signature": "hash_abc123"},
        {"asset_id": "Asset_11_AU_Sydney", "billing_month": "2025-11-01", "actual_billed_kwh": 6000.0, "inferred_kwh": 5900.0, "uploaded_pdf_hash": "TAMPERED_HASH_999", "original_crypto_signature": "VALID_SIGNATURE_888"},
        {"asset_id": "Asset_09_NZ_Boundary", "billing_month": "2025-11-01", "actual_billed_kwh": 1000.0, "inferred_kwh": 800.0, "uploaded_pdf_hash": "hash_valid_123", "original_crypto_signature": "hash_valid_123"},
        {"asset_id": "Asset_08_NZ_Boundary", "billing_month": "2025-11-01", "actual_billed_kwh": 9500.0, "inferred_kwh": 6000.0, "uploaded_pdf_hash": "hash_valid_456", "original_crypto_signature": "hash_valid_456"}
    ]
    
    file_name = "dim_invoices_proxy.csv"
    pd.DataFrame(data).to_csv(file_name, index=False)
    print(f"SUCCESS: Generated {file_name} in current directory.")

if __name__ == "__main__":
    generate_csv()