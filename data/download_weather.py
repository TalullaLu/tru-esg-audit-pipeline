import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}?sslmode={os.getenv('DB_SSLMODE', 'require')}"

engine = create_engine(db_url)
df = pd.read_sql("SELECT * FROM dim_auckland_weather", engine)
df.to_csv("data/external_auckland_weather.csv", index=False)
print(f"finished！total {len(df)} row")