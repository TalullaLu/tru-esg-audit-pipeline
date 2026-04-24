import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 1. Asset Configuration (Asset Master)
# Reflects the 17-asset structure: HQ, Data Centers, and Branches [cite: 131, 211]
assets = [
    {"Asset_ID": "NZ-HQ-AKL-01", "Type": "Office", "Region": "NZ", "Sqm": 5000, "Has_BMS": "Yes"},
    {"Asset_ID": "NZ-DC-AKL-01", "Type": "DataCenter", "Region": "NZ", "Sqm": 1200, "Has_BMS": "Yes"},
    {"Asset_ID": "NZ-BR-AKL-05", "Type": "Branch", "Region": "NZ", "Sqm": 300, "Has_BMS": "No"},
    # Note: Full production list includes all 17 multi-jurisdictional assets [cite: 203]
]

# 2. Time Range & Environmental Simulation (Auckland November: Late Spring)
start_date = datetime(2024, 11, 1)
end_date = datetime(2024, 11, 30, 23, 45)
timestamps = pd.date_range(start=start_date, end=end_date, freq='15min') # 15-min intervals [cite: 167]

# Simulate Auckland Temp (14°C - 22°C) to test cooling load correlations [cite: 174, 184]
temp_base = 18 + 4 * np.sin(np.arange(len(timestamps)) * (2 * np.pi / (24 * 4)))
temp_noise = np.random.normal(0, 1.5, len(timestamps))
temperatures = temp_base + temp_noise

# 3. Core Generation Engine
all_data = []

for asset in assets:
    for i, ts in enumerate(timestamps):
        is_weekend = ts.weekday() >= 5
        is_business_hour = 8 <= ts.hour <= 18
        
        # Base Load Logic
        if asset['Type'] == 'DataCenter':
            base_load = 50.0  # Stable high-density load [cite: 18]
        else:
            base_load = 5.0 if not is_business_hour else 15.0
            if is_weekend: base_load *= 0.4
            
        # Physics-based Cooling Load (HVAC signals correlation) [cite: 3, 138]
        cooling_load = max(0, (temperatures[i] - 18) * 1.2) if asset['Has_BMS'] == 'Yes' else 0
        
        total_kwh = base_load + cooling_load + np.random.normal(0, 0.5)
        
        # --- Audit "Mines" (Injected Anomalies for Layer 2 Testing) [cite: 181] ---
        # A. Sensor Failure: Zero-readings for HQ on Nov 15th
        if asset['Asset_ID'] == 'NZ-HQ-AKL-01' and ts.day == 15 and 2 <= ts.hour <= 4:
            total_kwh = 0
            
        # B. Night-time Spike: HVAC/Lights left on at a Branch [cite: 187, 293]
        if asset['Asset_ID'] == 'NZ-BR-AKL-05' and ts.day == 10 and ts.hour == 2:
            total_kwh = 25.0 
            
        all_data.append({
            "Timestamp": ts,
            "Asset_ID": asset['Asset_ID'],
            "Total_kWh": round(max(0, total_kwh), 4),
            "Outdoor_Temp": round(temperatures[i], 2),
            "Is_Business_Hour": is_business_hour,
            "Region": asset['Region']
        })

# 4. Export to CSV (Layer 1 Landing Zone) [cite: 242, 253]
df = pd.DataFrame(all_data)
df.to_csv("raw_sensor_data_202411.csv", index=False)
print(f"Successfully generated {len(df)} rows. Dataset saved as raw_sensor_data_202411.csv")