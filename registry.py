# TRU_registry.py

# 1. Audit Policy Definition (12 Core Scenarios + Scope 3)
AUDIT_POLICIES = {
    "S01_L0_UNAUTHORIZED_ASSET": {"check": "MAC_AUTH", "enabled": True},
    "S02_L1_TAMPERED_PDF": {"check": "SHA256_MATCH", "enabled": True},
    "S03_L1_TIMESERIES_GAP": {"check": "MONTHLY_COMPLETENESS", "min_pct_limit": 0.95, "enabled": True},
    "S04_L2_METER_LEAKAGE": {"check": "SUBMETER_BAL", "max_diff": 0.10, "duration_trigger_mins": 60, "enabled": True},
    "S05_L2_AFTER_HOURS_SPIKE": {"check": "Z_SCORE", "sigma_limit": 3.0, "duration_trigger_mins": 60, "enabled": True},
    "S06_L2_IEQ_GREENWASHING": {"check": "CO2_THRESHOLD", "indoor_co2_limit": 1000, "duration_trigger_mins": 30, "enabled": True},
    "S07_L2_EFFICIENCY_DEGRADATION": {"check": "CUSUM_DAILY_HVAC", "slack_pct": 0.10, "threshold_sigma": 5.0, "enabled": True},
    "S08_L4_SYNC_DELAY": {"check": "HR_ENERGY_LAG", "source": "fact_hr_occupancy", "lag_days_trigger": 7, "enabled": True},
    "S09_L4_BILLING_ESTIMATION_VARIANCE": {"check": "PROXY_BASELINE", "variance_limit": 0.15, "enabled": True},
    "S10_L2_NABERSNZ_GAP": {"check": "BASELINE_DEV", "max_delta_limit": 0.10, "enabled": True},
    "S11_L3_TRAVEL_FRAUD": {"check": "SHORT_HAUL_BUSINESS_CLASS", "max_flight_hours": 4, "enabled": True},
    "S12_SCOPE3_WASTE_COMPLIANCE": {"check": "CERT_MISSING", "enabled": True}
}

# 2. Asset Master Data (The Physical Footprint)
# Location mapping added for Looker Studio aggregation
ASSET_SPACE_REGISTRY = {
    "Asset_01_NZ_Boundary": {"area_sqm": 1200.0, "occupant_count": 45,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "Auckland HQ / L5"},
    "Asset_02_NZ_Boundary": {"area_sqm": 2500.0, "occupant_count": 100, "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "Auckland HQ / L6"},
    "Asset_03_NZ_Boundary": {"area_sqm": 800.0,  "occupant_count": 35,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "Auckland HQ / L7"},
    "Asset_04_NZ_Boundary": {"area_sqm": 3200.0, "occupant_count": 145, "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "10 Queen St / L3"},
    "Asset_05_NZ_Boundary": {"area_sqm": 1500.0, "occupant_count": 65,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "10 Queen St / L4"},
    "Asset_06_NZ_Boundary": {"area_sqm": 4000.0, "occupant_count": 95,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "Fanshawe St Campus"},
    "Asset_07_NZ_Boundary": {"area_sqm": 950.0,  "occupant_count": 40,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "45 Shortland St"},
    "Asset_08_NZ_Boundary": {"area_sqm": 2100.0, "occupant_count": 75,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "Wynyard Quarter Office"},
    "Asset_09_NZ_Boundary": {"area_sqm": 1100.0, "occupant_count": 40,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "HIGH_DEMAND", "display_name": "Commercial Bay Tower / L28"},
    "Asset_10_NZ_Boundary": {"area_sqm": 1800.0, "occupant_count": 62,  "region": "NZ", "location": "Auckland_HQ", "has_iot": True, "space_designation": "STANDARD", "display_name": "Viaduct Harbour Office"},
    "Asset_11_AU_Sydney":   {"area_sqm": 1000.0, "occupant_count": 55,  "region": "AU", "location": "Sydney_Office", "has_iot": False, "space_designation": "STANDARD", "display_name": "Sydney Office / 88 Phillip St"},
}

# Authorized assets for telemetry intake
AUTHORIZED_IOT_ASSETS = [k for k, v in ASSET_SPACE_REGISTRY.items() if v["has_iot"]]