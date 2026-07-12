import pandas as pd

def create_reference_files():
    # Strict compliance parameters for all scenarios
    compliance_data = [
        {"Parameter_Category": "UTILITY", "Region": "NZ", "Effective_Year": 2025, "Target_Tier": "OFFICIAL", "Metric_Value": 0.25, "Unit": "AUD/kWh"},
        {"Parameter_Category": "EMISSION_FACTOR", "Region": "NZ", "Effective_Year": 2025, "Target_Tier": "OFFICIAL", "Metric_Value": 0.11, "Unit": "kgCO2e/kWh"},
        {"Parameter_Category": "NABERS_BASE_TARGET", "Region": "NZ", "Effective_Year": 2025, "Target_Tier": "5_STAR", "Metric_Value": 42.0, "Unit": "MJ/sqm"}
    ]
    pd.DataFrame(compliance_data).to_csv("data/dim_esg_compliance_parameters.csv", index=False)
    
    # Scope 3 baseline
    scope3_data = [{"Category": "Travel", "Baseline": 100}]
    pd.DataFrame(scope3_data).to_csv("data/scope3_reference_data.csv", index=False)
    print("Reference files generated successfully.")

if __name__ == "__main__":
    create_reference_files()