import pandas as pd
import numpy as np
from pathlib import Path
from registry import ASSET_SPACE_REGISTRY

pd.options.mode.chained_assignment = None

BASE_PATH = Path(__file__).resolve().parent
DATA_PATH = BASE_PATH / "data"


# ── Parameter constants (from dim_esg_compliance_parameters) ──────────────────
ELEC_RATE_NZD      = 0.25        # NZD per kWh
EMISSION_FACTOR_NZ = 0.11        # kgCO2e per kWh  (MfE 2025)
CO2_THRESHOLD_PPM  = 1000        # IEQ breach threshold (S06)
IEQ_MIN_INTERVALS  = 2           # >= 30 minutes continuous
GAP_MIN_INTERVALS  = 4           # >= 1 hour continuous (S04)
DATA_COMPLETENESS_THRESHOLD = 0.95
EXPECTED_ROWS_PER_ASSET = 2880   # 15-min intervals across November


def get_col(df, candidates):
    """Return the first matching column name from candidates list."""
    lower = {str(c).lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lower:
            return lower[name.lower()]
    return candidates[0]


def extract_events(df_asset, condition_series, min_intervals):
    """
    Group consecutive True rows into events.
    Only return events with length >= min_intervals.
    """
    df_asset = df_asset.copy()
    df_asset['_breach'] = condition_series.values
    df_asset['_block'] = (df_asset['_breach'] != df_asset['_breach'].shift()).cumsum()
    events = []
    for _, group in df_asset[df_asset['_breach']].groupby('_block'):
        if len(group) >= min_intervals:
            events.append(group)
    return events


def calc_financial(waste_kwh):
    """
    Returns (financial_cost_nzd, carbon_kg_co2e) for a given waste_kwh.
    """
    financial_cost = round(waste_kwh * ELEC_RATE_NZD, 2)
    carbon_kg      = round(waste_kwh * EMISSION_FACTOR_NZ, 3)  # kgCO2e
    return financial_cost, carbon_kg


def run_facility_audit():
    print("=" * 60)
    print("Facility Audit Engine  —  S01 | S03 | S06 | S08")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────────────────────
    try:
        telemetry = pd.read_csv(DATA_PATH / "fact_telemetry_ledger.csv")
        weather   = pd.read_csv(DATA_PATH / "external_auckland_weather.csv")
        exemptions = pd.read_csv(DATA_PATH / "fact_exemption_registry.csv")
        exemptions['start_time'] = pd.to_datetime(exemptions['start_time'])
        exemptions['end_time']   = pd.to_datetime(exemptions['end_time'])

    except Exception as e:
        print(f"CRITICAL: Failed to load data -> {e}")
        return

    # Parse timestamps
    telemetry['timestamp'] = pd.to_datetime(telemetry['timestamp'])
    weather['timestamp']   = pd.to_datetime(weather['timestamp'])

    # Merge outdoor temperature into telemetry on timestamp
    telemetry = telemetry.merge(
        weather[['timestamp', 'outdoor_temp_c', 'day_type']],
        on='timestamp', how='left'
    )

    # Identify column names dynamically
    c_asset   = get_col(telemetry, ['asset_id', 'mac_address'])
    c_tot     = get_col(telemetry, ['total_power_kw', 'total_power'])
    c_co2     = get_col(telemetry, ['indoor_co2_ppm', 'co2_ppm', 'co2'])
    c_in_temp = get_col(telemetry, ['indoor_temp_c', 'in_temp', 'indoor_temp'])

    audit_ledger = []

    def is_exempt(asset_id, scenario_id, timestamp):
        if exemptions.empty:
            return False
        mask = (
            (exemptions['asset_id']    == asset_id) &
            (exemptions['scenario_id'] == scenario_id) &
            (exemptions['start_time'] <= timestamp) &
            (exemptions['end_time']   >= timestamp)
        )
        return mask.any()
    def log_event(start_t, end_t, asset, scenario, status,
                  area, duration_mins, assessed_mins,
                  waste_kwh, financial_cost, carbon_kg):
        audit_ledger.append({
            "start_time":          start_t,
            "end_time":            end_t,
            "asset_id":            asset,
            "scenario":            scenario,
            "status":              status,
            "area_sqm":            area,
            "anomaly_duration_mins": int(duration_mins),
            "total_assessed_mins": int(assessed_mins),
            "waste_kwh":           round(float(waste_kwh), 4),
            "financial_cost":      float(financial_cost),
            "carbon_kg":          float(carbon_kg),
        })

    # ── S01: UNAUTHORIZED ASSET ───────────────────────────────────────────────
    # Trigger: any MAC / asset_id not in registry → instant, no duration needed
    valid_assets = set(ASSET_SPACE_REGISTRY.keys())
    for asset in telemetry[c_asset].unique():
        if asset not in valid_assets:
            ghost = telemetry[telemetry[c_asset] == asset]
            # Unverified kWh = sum of total_power × 15-min interval
            kwh_unverified = ghost[c_tot].sum() * 0.25 if c_tot in ghost.columns else 0.0
            
            log_event(
                ghost['timestamp'].min(), ghost['timestamp'].max(),
                asset, 'S01', 'L0_UNAUTHORIZED_ASSET',
                0.0, len(ghost) * 15, len(ghost) * 15,
                0.0, 0.0, 0.0
            )
            print(f"  [S01] Rogue asset detected: {asset}  |  "
                  f"Unverified kWh={kwh_unverified:.1f}  |  "
                  f"Financial quarantined — excluded from all KPI calculations")

    # ── Per-asset loop: S03, S06 ──────────────────────────────────────────────
    for asset_id, info in ASSET_SPACE_REGISTRY.items():
        if not info.get("has_iot", False):
            continue

        df = (telemetry[telemetry[c_asset] == asset_id]
              .sort_values('timestamp')
              .reset_index(drop=True))
        if df.empty:
            continue

        area          = info.get('area_sqm', 0.0)
        assessed_mins = max(
            int((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60),
            15
        )

        # ── S03: TELEMETRY DATA GAP ───────────────────────────────────────────
        # Trigger: actual row count < 95% of expected 2,880
        completeness = len(df) / EXPECTED_ROWS_PER_ASSET
        if completeness < DATA_COMPLETENESS_THRESHOLD:
            # Reconstruct expected full timestamp index at 15-min frequency
            # then count actual gaps precisely — avoids off-by-one from
            # using EXPECTED_ROWS_PER_ASSET as a fixed constant
            full_index = pd.date_range(
                start=df['timestamp'].min(),
                end=df['timestamp'].max(),
                freq='15min'
            )
            actual_set  = set(df['timestamp'])
            missing_rows = sum(1 for t in full_index if t not in actual_set)
            missing_mins = missing_rows * 15
            log_event(
                df['timestamp'].min(), df['timestamp'].max(),
                asset_id, 'S03', 'L1_TIMESERIES_GAP',
                area, missing_mins, assessed_mins,
                0.0, 0.0, 0.0
            )
            print(f"  [S03] {asset_id}: completeness={completeness:.1%}  |  "
                  f"Missing {missing_rows} rows ({missing_mins} mins)")

        # ── S06: IEQ GREENWASHING ─────────────────────────────────────────────
        # Trigger: CO2 > 1000 ppm continuously for >= 2 intervals (>= 30 mins)
        # Single condition only — CO2 is the definitive proxy for ventilation

        if c_co2 not in df.columns:
            print(f"  [S06] WARNING: CO2 column not found for {asset_id}, skipping S06.")
        else:
            cond_s06 = df[c_co2] > CO2_THRESHOLD_PPM
            events   = extract_events(df, cond_s06, min_intervals=IEQ_MIN_INTERVALS)
            for ev in events:
                duration_mins = len(ev) * 15
                log_event(
                    ev['timestamp'].iloc[0], ev['timestamp'].iloc[-1],
                    asset_id, 'S06', 'L1_IEQ_GREENWASHING',
                    area, duration_mins, assessed_mins,
                    0.0, 0.0, 0.0
                )
                audit_ledger[-1].update({
                    'recommendation': 'Monitor and increase fresh air supply',
                })
                print(f"  [S06] {asset_id}: IEQ breach  |  "
                      f"CO2 peak={ev[c_co2].max():.0f} ppm  |  "
                      f"Duration={duration_mins} mins")
        
        # ── S08: HIGH-DEMAND ZONE IEQ OPTIMISATION ────────────────────────
        # Only applies to assets with space_designation = HIGH_DEMAND
        # Trigger: CO2 > 800ppm OR temp outside 21-23°C, sustained >= 2 intervals
        # Output: L2_HIGH_DEMAND_IEQ_GAP with cognitive productivity loss estimate
        # Standard: WELL Building Standard v2
        # Financial: occupants × avg_salary × 0.15 × (duration_mins / 124,800)

        if info.get('space_designation') == 'HIGH_DEMAND':
            CO2_HD_THRESHOLD  = 800       # ppm — WELL v2 enhanced standard
            TEMP_HD_MIN       = 21.0      # °C
            TEMP_HD_MAX       = 23.0      # °C
            HD_MIN_INTERVALS  = 2         # >= 30 minutes
            AVG_SALARY_NZD    = 300000    # NZD/year — high-value professional
            COGNITIVE_COEFF   = 0.15      # 15% impairment (Allen et al. 2019, Harvard)
            WORKING_MINS_YEAR = 124800    # 260 days × 8hrs × 60mins

            occupants = info.get('occupant_count', 0)

            cond_s08 = (
                (df[c_co2] > CO2_HD_THRESHOLD) |
                (df[c_in_temp] < TEMP_HD_MIN) |
                (df[c_in_temp] > TEMP_HD_MAX)
            )

            events_s08 = extract_events(df, cond_s08, HD_MIN_INTERVALS)

            for ev in events_s08:
                if is_exempt(asset_id, 'S08', ev['timestamp'].iloc[0]):
                    continue
                duration_mins = len(ev) * 15

                # Cognitive productivity loss (total across all occupants)
                cognitive_loss_nzd = round(
                    occupants * AVG_SALARY_NZD * COGNITIVE_COEFF
                    * (duration_mins / WORKING_MINS_YEAR), 2
                )

                # No energy waste — impact is productivity loss, not energy cost
                log_event(
                    ev['timestamp'].iloc[0], ev['timestamp'].iloc[-1],
                    asset_id, 'S08', 'L2_HIGH_DEMAND_IEQ_GAP',
                    area, duration_mins, assessed_mins,
                    0.0, 0.0, 0.0
                )
                # S08 extra fields written directly to ledger
                audit_ledger[-1].update({
                    'cognitive_loss_nzd': cognitive_loss_nzd,
                    'avg_co2_ppm':        round(ev[c_co2].mean(), 0),
                    'peak_co2_ppm':       int(ev[c_co2].max()),
                    'occupants':          occupants,
                    'recommendation':     'Monitor and increase fresh air supply',
                })
                print(f"  [S08] {asset_id}: IEQ gap {duration_mins} mins | "
                      f"CO2 peak={int(ev[c_co2].max())}ppm | "
                      f"cognitive loss=NZD {cognitive_loss_nzd:,.0f}")
                
    # ── Write output ──────────────────────────────────────────────────────────
    if audit_ledger:
        out_path = DATA_PATH / "facility_audit_log.csv"
        pd.DataFrame(audit_ledger).to_csv(out_path, index=False)
        print(f"\nFacility Audit complete — {len(audit_ledger)} events logged.")
        print(f"Output: {out_path}")
    else:
        print("\nFacility Audit complete — no events detected.")


if __name__ == "__main__":
    run_facility_audit()
