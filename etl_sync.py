import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def sync_cloud_to_local():
    # Connect to your cloud database
    db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
    engine = create_engine(db_url)
    
    # Query the data you just uploaded
    query = 'SELECT * FROM "fact_telemetry_ledger" ORDER BY timestamp ASC'
    df = pd.read_sql(query, engine)
    
    # Ensure data directory exists
    if not os.path.exists("data"):
        os.makedirs("data")
        
    # Save locally so the audit engines can read it
    df.to_csv("data/fact_telemetry_ledger.csv", index=False)
    print("SUCCESS: Cloud data synced to data/fact_telemetry_ledger.csv")

if __name__ == "__main__":
    sync_cloud_to_local()