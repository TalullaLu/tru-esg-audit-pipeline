import os

import random

import datetime

import pandas as pd

from dotenv import load_dotenv

from sqlalchemy import create_engine, text



load_dotenv()



def generate_7_scenario_mock_data():

    db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}?sslmode={os.getenv('DB_SSLMODE', 'require')}"

    engine = create_engine(db_url, pool_pre_ping=True)

   

print("[1/5] Connecting to Google Cloud SQL...")
engine = None
weather_rows = []
try:
    with engine.connect() as conn:
        weather_rows = conn.execute(text(
            "SELECT timestamp::timestamp, outdoor_temp_c, day_type FROM dim_auckland_weather ORDER BY timestamp ASC;"
        )).fetchall()
    print(f"[2/5] Successfully loaded {len(weather_rows)} weather anchors from cloud.")
except Exception as e:
    print(f"[2/5] Cloud unavailable ({e}), falling back to local CSV...")
    weather_df = pd.read_csv("data/external_auckland_weather.csv")
    weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
    weather_rows = list(weather_df[['timestamp', 'outdoor_temp_c', 'day_type']].itertuples(index=False, name=None))
    print(f"      Loaded {len(weather_rows)} weather rows from local CSV.")
   

    valid_assets = [f"Asset_{i:02d}_NZ_Boundary" for i in range(1, 11)]

    bulk_records = []

    start_date = weather_rows[0][0].date()

   

    for row in weather_rows:

        current_time = row[0]

        ext_temp = float(row[1])

        day_type = str(row[2])

        days_elapsed = (current_time.date() - start_date).days

       

        if current_time.day == 20 and current_time.hour == 12 and current_time.minute == 0:

            bulk_records.append({

                "timestamp": current_time,

                "asset_id": "Asset_99_UNKNOWN_Boundary",

                "indoor_co2_ppm": 600,

                "indoor_temp_c": 22.0,

                "total_power_kw": 65.0,

                "hvac_power_kw": 35.0,

                "lighting_power_kw": 15.0,

                "it_load_power_kw": 15.0,

                "emissions_co2_kg": 6.175,

                "audit_trait": "L0_UNAUTHORIZED_ASSET",

                "crypto_signature": "sig_rogue99"

            })

           

        for asset in valid_assets:

            if asset == "Asset_03_NZ_Boundary" and datetime.datetime(2025, 11, 15) <= current_time < datetime.datetime(2025, 11, 17):

                continue

               

            base_hvac = max(15.0, (ext_temp - 14.0) * 4.5) if day_type == "WEEKDAY" else 5.0

            base_lighting = 8.0 if (6 <= current_time.hour <= 20 and day_type == "WEEKDAY") else 1.5

            base_it = 12.0 + random.uniform(-0.5, 0.5)

           

            indoor_co2 = random.randint(550, 750) if day_type == "WEEKDAY" else random.randint(400, 450)

            indoor_temp = 21.5 + random.uniform(-0.5, 0.5)

            audit_trait = "L0_CLEAN_COMPLIANT"

           

            if asset == "Asset_02_NZ_Boundary" and ext_temp > 22.0 and day_type == "WEEKDAY" and (11 <= current_time.hour <= 15):

                indoor_co2 = 1250          

                base_hvac = 12.0          

                indoor_temp = 23.8        

                base_lighting = 8.0

                base_it = 12.0

                audit_trait = "L3_GREENWASH_RISK"

               

            elif asset == "Asset_04_NZ_Boundary" and current_time.day == 10 and (8 <= current_time.hour <= 16):

                indoor_temp = 14.5        

                indoor_co2 = 800

                base_hvac = 1.0            

                base_lighting = 2.0

                base_it = 2.0              

                audit_trait = "L1_METER_FAULT"

               

            elif asset == "Asset_06_NZ_Boundary" and datetime.datetime(2025, 11, 27) <= current_time <= datetime.datetime(2025, 11, 30, 23, 45):

                base_hvac = max(15.0, (ext_temp - 14.0) * 4.5) if day_type == "WEEKDAY" else 5.0

                base_lighting = 8.0 if (6 <= current_time.hour <= 20 and day_type == "WEEKDAY") else 1.5

                base_it = 12.0 + random.uniform(-0.5, 0.5)

                audit_trait = "L1_METER_FAULT"

               

            elif asset == "Asset_05_NZ_Boundary":

                if days_elapsed >= 11:

                    degradation_factor = (days_elapsed - 11) * 0.85  

                    base_hvac += degradation_factor

                    audit_trait = "L2_EFFICIENCY_DEGRADATION"

                else:

                    audit_trait = "L0_CLEAN_COMPLIANT"
        
            elif asset == "Asset_01_NZ_Boundary":
                base_it += 20.0
                audit_trait = "L2_HIGH_IT_LOAD"
                
            elif asset == "Asset_09_NZ_Boundary":
                if day_type == "WEEKDAY" and (14 <= current_time.hour <= 17):
                    indoor_co2 = random.choice([820, 850, 780, 810, 760, 830])
                    audit_trait = "L2_HIGH_DEMAND_IEQ_GAP"
                else:
                    audit_trait = "L0_CLEAN_COMPLIANT"

            elif day_type == "WEEKEND" and current_time.day in [1, 2] and (10 <= current_time.hour <= 22):

                base_hvac = 35.0          

                base_lighting = 15.0      

                audit_trait = "L2_BEHAVIOR_ANOMALY"



            if audit_trait == "L1_METER_FAULT" and asset == "Asset_06_NZ_Boundary":

                total_power = 45.0        

            elif audit_trait == "L1_METER_FAULT" and asset == "Asset_04_NZ_Boundary":

                total_power = 5.0          

            else:

                total_power = round(base_hvac + base_lighting + base_it, 2)

               

            bulk_records.append({

                "timestamp": current_time,

                "asset_id": asset,

                "indoor_co2_ppm": indoor_co2,

                "indoor_temp_c": round(indoor_temp, 2),

                "total_power_kw": total_power,

                "hvac_power_kw": round(base_hvac, 2),

                "lighting_power_kw": round(base_lighting, 2),

                "it_load_power_kw": round(base_it, 2),

                "emissions_co2_kg": round(total_power * 0.095, 3),

                "audit_trait": audit_trait,

                "crypto_signature": f"sig_{random.getrandbits(32):x}"

            })



print(f"[4/5] Data matrix ready. Convert to DataFrame: {len(bulk_records)} rows.")
df_ledger = pd.DataFrame(bulk_records)
print("      Executing data pipeline...")
try:
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS "fact_telemetry_ledger" CASCADE;'))
    df_ledger.to_sql(
        name="fact_telemetry_ledger",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi"
    )
    print("[5/5] SUCCESS: Telemetry data uploaded to Google Cloud SQL.")
except Exception as e:
    print(f"[5/5] Cloud unavailable, saving to local CSV...")
    df_ledger.to_csv("data/fact_telemetry_ledger.csv", index=False)
    print("      Saved to data/fact_telemetry_ledger.csv")


if __name__ == "__main__":

    generate_7_scenario_mock_data() 


