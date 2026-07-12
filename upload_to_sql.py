import pandas as pd
from sqlalchemy import create_engine
import os
import sys
from dotenv import load_dotenv

# 1. Absolute Path Resolution (Locks down the directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

# 2. Dependency Check
try:
    import registry
except ImportError:
    print(f"CRITICAL ERROR: 'registry.py' not found in {SCRIPT_DIR}")
    sys.exit(1)

load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# 3. File Check Utility
def check_file(filename):
    filepath = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(filepath):
        print(f"CRITICAL ERROR: '{filename}' is missing from {SCRIPT_DIR}")
        sys.exit(1)
    return filepath

# 4. Database Connection
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME')

if not all([db_user, db_password, db_host, db_name]):
    print("CRITICAL ERROR: Database credentials missing. Check your .env file.")
    sys.exit(1)

engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

# 5. Execution Process
print("Starting upload process...")

comp_file = check_file("dim_esg_compliance_parameters.csv")
pd.read_csv(comp_file).to_sql("dim_esg_compliance_parameters", engine, if_exists="replace", index=False)
print("Compliance parameters uploaded.")

scope3_file = check_file("scope3_reference_data.csv")
pd.read_csv(scope3_file).to_sql("ref_scope3_standards", engine, if_exists="replace", index=False)
print("Scope 3 standards uploaded.")

telemetry_file = check_file("fact_telemetry_ledger.csv")
df = pd.read_csv(telemetry_file)

asset_map = {k: v['display_name'] for k, v in registry.ASSET_SPACE_REGISTRY.items()}
df['location'] = df['asset_id'].map(asset_map)

df.to_sql("fact_telemetry_ledger", engine, if_exists="replace", index=False)
print("SUCCESS: Telemetry data with location uploaded.")