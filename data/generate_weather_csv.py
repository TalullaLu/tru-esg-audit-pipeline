import os
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def fetch_and_save_auckland_weather():
    print("Connecting to Open-Meteo Historical Archive API...")
    api_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": -36.8485,
        "longitude": 174.7633,
        "start_date": "2025-11-01",
        "end_date": "2025-11-30",
        "hourly": "temperature_2m",
        "timezone": "Pacific/Auckland"
    }
    
    response = requests.get(api_url, params=params)
    if response.status_code != 200:
        raise RuntimeError(f"API Connection Failed: {response.status_code}")
        
    data = response.json()
    hourly_records = data["hourly"]
    
    df_hourly = pd.DataFrame({
        "timestamp": pd.to_datetime(hourly_records["time"]),
        "outdoor_temp_c": hourly_records["temperature_2m"]
    })
    
    df_hourly.set_index("timestamp", inplace=True)
    df_15min = df_hourly.resample("15Min").interpolate(method="linear").reset_index()
    
    df_15min["day_type"] = df_15min["timestamp"].dt.weekday.apply(lambda x: "WEEKEND" if x >= 5 else "WEEKDAY")
    df_15min["timestamp"] = df_15min["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df_15min["outdoor_temp_c"] = df_15min["outdoor_temp_c"].round(2)


    # === ANOMALY INJECTION FOR S06 ===
    # Convert to datetime to create a mask for the specific time window
    df_15min["timestamp_dt"] = pd.to_datetime(df_15min["timestamp"])
    mask_s06 = (df_15min["timestamp_dt"] >= "2025-11-25 14:00:00") & \
               (df_15min["timestamp_dt"] <= "2025-11-25 15:00:00")
    df_15min.loc[mask_s06, "outdoor_temp_c"] = 26.5
    df_15min = df_15min.drop(columns=["timestamp_dt"])
    # === END ANOMALY INJECTION ===

    db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}?sslmode={os.getenv('DB_SSLMODE', 'require')}"
    
    db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}?sslmode={os.getenv('DB_SSLMODE', 'require')}"
    engine = create_engine(db_url, pool_pre_ping=True)
    
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS "dim_auckland_weather" CASCADE;'))
        conn.execute(text("""
            CREATE TABLE dim_auckland_weather (
                timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                outdoor_temp_c NUMERIC NOT NULL,
                day_type TEXT NOT NULL
            );
        """))
        
        insert_sql = text("INSERT INTO dim_auckland_weather (timestamp, outdoor_temp_c, day_type) VALUES (:timestamp, :outdoor_temp_c, :day_type);")
        conn.execute(insert_sql, df_15min.to_dict(orient="records"))
        
    print("SUCCESS: Weather pipeline operational.")

if __name__ == "__main__":
    fetch_and_save_auckland_weather()