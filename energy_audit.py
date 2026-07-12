# energy_audit.py
# IoT Energy Audit Engine — S04 | S05 | S07 | S10
# Covers: Sub-meter leakage, After-hours idle, Efficiency drift, NABERSNZ compliance

import pandas as pd
import numpy as np
from pathlib import Path
from registry import ASSET_SPACE_REGISTRY

pd.options.mode.chained_assignment = None

BASE_PATH = Path(__file__).resolve().parent
DATA_PATH = BASE_PATH / "data"

# ── Parameters (sourced from dim_esg_compliance_parameters) ───────────────────
ELEC_RATE_NZD        = 0.25      # NZD/kWh
EMISSION_FACTOR_NZ   = 0.11      # kgCO2e/kWh  (MfE 2025)
CDD_BASE_TEMP        = 18.3      # °C  (AS/NZS 3598.1:2014)
NABERSNZ_BASE_MJ     = 42.0      # MJ/sqm  (5-star base)
NABERSNZ_CDD_MULT    = 0.08      # MJ/CDD  (climate adjustment)
KWH_TO_MJ            = 3.6

# Trigger thresholds
S04_LEAKAGE_PCT      = 0.10      # >10% gap between total and sub-meters
S04_MIN_INTERVALS    = 4         # >= 4 × 15min = 1 hour sustained
S05_MIN_INTERVALS    = 4         # >= 4 × 15min = 1 hour sustained
S07_ROLLING_WINDOW   = 7 * 96   # 7-day rolling window (intervals)
S07_RESIDUAL_PCT     = 0.20      # rolling residual > 20% of predicted
S10_OVERRUN_RATIO    = 1.10      # YTD actual > 110% of NABERSNZ budget
COMPLETENESS_THRESH  = 0.95      # minimum data completeness for S07/S10
EXPECTED_ROWS        = 2880      # 15-min intervals across November


def calc_financial(waste_kwh: float):
    """Return (financial_cost_nzd, carbon_kg) for a given waste_kwh."""
    financial_cost = round(waste_kwh * ELEC_RATE_NZD, 2)
    carbon_kg      = round(waste_kwh * EMISSION_FACTOR_NZ, 3)
    return financial_cost, carbon_kg


def extract_events(df_asset: pd.DataFrame, condition: pd.Series, min_intervals: int):
    """
    Group consecutive True rows into sustained events.
    Returns only events with length >= min_intervals.
    Each returned group has a clean reset index.
    """
    df_asset = df_asset.copy().reset_index(drop=True)
    df_asset['_breach'] = condition.values
    df_asset['_block']  = (df_asset['_breach'] != df_asset['_breach'].shift()).cumsum()
    events = []
    for _, grp in df_asset[df_asset['_breach']].groupby('_block'):
        if len(grp) >= min_intervals:
            events.append(grp.reset_index(drop=True))
    return events


def run_energy_audit():
    print("=" * 60)
    print("Energy Audit Engine  —  S04 | S05 | S07 | S10")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────────────────────
    try:
        telemetry  = pd.read_csv(DATA_PATH / "fact_telemetry_ledger.csv")
        weather    = pd.read_csv(DATA_PATH / "external_auckland_weather.csv")
        models     = pd.read_csv(DATA_PATH / "dim_asset_regression_models.csv")
        exemptions = pd.read_csv(DATA_PATH / "fact_exemption_registry.csv")
    except Exception as e:
        print(f"CRITICAL: Failed to load data -> {e}")
        return

    # ── Parse and enrich telemetry ────────────────────────────────────────────
    telemetry['timestamp'] = pd.to_datetime(telemetry['timestamp'])
    weather['timestamp']   = pd.to_datetime(weather['timestamp'])

    telemetry = telemetry.merge(
        weather[['timestamp', 'outdoor_temp_c', 'day_type']],
        on='timestamp', how='left'
    )
    telemetry['hour']       = telemetry['timestamp'].dt.hour
    telemetry['is_weekday'] = (telemetry['day_type'] == 'WEEKDAY').astype(int)
    telemetry['cdd']        = (telemetry['outdoor_temp_c'] - CDD_BASE_TEMP).clip(lower=0)

    # ── Exemption helper ──────────────────────────────────────────────────────
    if not exemptions.empty:
        exemptions['start_time'] = pd.to_datetime(exemptions['start_time'])
        exemptions['end_time']   = pd.to_datetime(exemptions['end_time'])

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

    # ── S05 baseline: clean data only ────────────────────────────────────────
    # Exclude anomaly rows so degradation/idle spikes don't inflate sigma
    clean = telemetry[telemetry['audit_trait'] == 'L0_CLEAN_COMPLIANT']
    baselines = (
        clean.groupby(['asset_id', 'hour'])['hvac_power_kw']
        .agg(mean='mean', std='std')
        .reset_index()
    )
    baselines['limit_3sigma'] = baselines['mean'] + 3 * baselines['std']
    print(f"  [S05] Clean baseline: {len(clean):,} rows "
          f"(excluded {len(telemetry)-len(clean):,} anomaly rows)")

    # ── Regression model lookup ───────────────────────────────────────────────
    model_lookup = models.set_index('asset_id').to_dict(orient='index')

    # ── Audit ledger ──────────────────────────────────────────────────────────
    audit_ledger = []
    nabersnz_summary = []

    def log_event(asset, scenario, status, start_t, end_t,
                  area, duration_mins, assessed_mins,
                  waste_kwh, financial_cost, carbon_kg, extra=None):
        record = {
            "timestamp":             start_t,
            "end_time":              end_t,
            "asset_id":              asset,
            "scenario":              scenario,
            "status":                status,
            "area_sqm":              area,
            "anomaly_duration_mins": int(duration_mins),
            "total_assessed_mins":   int(assessed_mins),
            "waste_kwh":             round(float(waste_kwh), 4),
            "financial_cost":        round(float(financial_cost), 2),
            "carbon_kg":            round(float(carbon_kg), 3),
        }
        if extra:
            record.update(extra)
        audit_ledger.append(record)

    # ═════════════════════════════════════════════════════════════════════════
    # Per-asset processing
    # ═════════════════════════════════════════════════════════════════════════
    for asset_id, info in ASSET_SPACE_REGISTRY.items():
        if not info.get("has_iot", False):
            continue

        df = (telemetry[telemetry['asset_id'] == asset_id]
              .sort_values('timestamp')
              .reset_index(drop=True))
        if df.empty:
            continue

        area          = info.get('area_sqm', 0.0)
        completeness  = len(df) / EXPECTED_ROWS
        assessed_mins = max(
            int((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60),
            15
        )

        # ── S04: SUB-METER CALIBRATION DRIFT ──────────────────────────────
        # Trigger: |total - (hvac+lighting+it)| / total > 10%
        #          sustained >= 4 consecutive intervals (>= 1 hour)
        df['sub_sum']    = (df['hvac_power_kw'] +
                            df['lighting_power_kw'] +
                            df['it_load_power_kw'])
        df['diff_ratio'] = ((df['total_power_kw'] - df['sub_sum']).abs()
                            / (df['total_power_kw'] + 1e-6))

        for ev in extract_events(df, df['diff_ratio'] > S04_LEAKAGE_PCT, S04_MIN_INTERVALS):
            if is_exempt(asset_id, 'S04', ev['timestamp'].iloc[0]):
                continue
            duration_mins = len(ev) * 15
            avg_gap_kw    = (ev['total_power_kw'] - ev['sub_sum']).abs().mean()
            waste_kwh     = avg_gap_kw * (duration_mins / 60.0)
            fc, ct        = calc_financial(waste_kwh)
            log_event(asset_id, 'S04', 'L2_METER_LEAKAGE',
                      ev['timestamp'].iloc[0], ev['timestamp'].iloc[-1],
                      area, duration_mins, assessed_mins, waste_kwh, fc, ct,
                      extra={'avg_diff_ratio': round(ev['diff_ratio'].mean(), 4)})
            print(f"  [S04] {asset_id}: {duration_mins} mins | "
                  f"waste={waste_kwh:.2f} kWh | cost=NZD {fc}")

        # ── S05: AFTER-HOURS HVAC IDLE RUNNING ────────────────────────────
        # Trigger: HVAC > (mean_h + 3σ_h) during non-business hours
        #          sustained >= 4 intervals (>= 1 hour)
        after_hours = (
            (df['day_type'] == 'WEEKEND') |
            ((df['day_type'] == 'WEEKDAY') & ((df['hour'] < 7) | (df['hour'] >= 20)))
        )
        df_ah = df[after_hours].copy().reset_index(drop=True)

        if not df_ah.empty and asset_id in baselines['asset_id'].values:
            bl = baselines[baselines['asset_id'] == asset_id].set_index('hour')
            df_ah['limit'] = df_ah['hour'].map(bl['limit_3sigma'])
            for ev in extract_events(df_ah, df_ah['hvac_power_kw'] > df_ah['limit'], S05_MIN_INTERVALS):
                if is_exempt(asset_id, 'S05', ev['timestamp'].iloc[0]):
                    continue
                duration_mins = len(ev) * 15
                waste_kwh     = (ev['hvac_power_kw'] - ev['limit']).clip(lower=0).sum() * 0.25
                fc, ct        = calc_financial(waste_kwh)
                log_event(asset_id, 'S05', 'L2_AFTER_HOURS_SPIKE',
                          ev['timestamp'].iloc[0], ev['timestamp'].iloc[-1],
                          area, duration_mins, assessed_mins, waste_kwh, fc, ct,
                          extra={'peak_hvac_kw': round(ev['hvac_power_kw'].max(), 2)})
                print(f"  [S05] {asset_id}: {duration_mins} mins | "
                      f"waste={waste_kwh:.2f} kWh | cost=NZD {fc}")

        # ── S07: EQUIPMENT EFFICIENCY DEGRADATION (CUSUM) ─────────────────
        # Method: CUSUM (Cumulative Sum Control Chart) on daily HVAC kWh
        # Standard: ASHRAE Guideline 14 / IPMVP Option B M&V methodology
        #
        # Logic:
        #   1. Establish baseline from clean period (audit_trait = L0_CLEAN_COMPLIANT)
        #   2. Compute CUSUM = max(0, CUSUM_prev + (daily_hvac - baseline_mean - K))
        #      K = slack (10% of baseline) — ignore small natural variation
        #      H = threshold (5× baseline std dev) — alarm when drift accumulates
        #   3. First day CUSUM > H is the alarm date
        #   4. Waste = excess HVAC kWh above baseline across all degraded days
        #
        # SKIP if completeness < 95% — gaps distort daily totals

        if completeness < COMPLETENESS_THRESH:
            print(f"  [S07] {asset_id}: SKIPPED (completeness={completeness:.1%})")
        else:
            df['date'] = df['timestamp'].dt.date
            daily = df.groupby('date').agg(
                hvac_kwh    =('hvac_power_kw',  lambda x: x.sum() * 0.25),
                audit_trait =('audit_trait',     lambda x: x.mode()[0]),
            ).reset_index()

            clean_days = daily[daily['audit_trait'] == 'L0_CLEAN_COMPLIANT']

            if len(clean_days) < 3:
                print(f"  [S07] {asset_id}: SKIPPED (insufficient clean baseline: "
                      f"{len(clean_days)} days)")
            else:
                mu    = clean_days['hvac_kwh'].mean()
                sigma = clean_days['hvac_kwh'].std()
                K     = 0.10 * mu
                H     = 5.0  * sigma

                cusum        = 0.0
                trigger_date = None
                for _, drow in daily.iterrows():
                    cusum = max(0.0, cusum + (drow['hvac_kwh'] - mu - K))
                    if trigger_date is None and cusum > H:
                        trigger_date = drow['date']

                if trigger_date is not None:
                    if not is_exempt(asset_id, 'S07', pd.Timestamp(trigger_date)):
                        deg_days  = daily[daily['audit_trait'] != 'L0_CLEAN_COMPLIANT']
                        waste_kwh = float((deg_days['hvac_kwh'] - mu).clip(lower=0).sum())
                        duration_mins = len(deg_days) * 24 * 60
                        fc, ct_tax    = calc_financial(waste_kwh)
                        deg_df  = df[df['audit_trait'] != 'L0_CLEAN_COMPLIANT']
                        start_t = deg_df['timestamp'].min()
                        end_t   = deg_df['timestamp'].max()
                        log_event(
                            asset_id, 'S07', 'L2_EFFICIENCY_DEGRADATION',
                            start_t, end_t,
                            area, duration_mins, assessed_mins,
                            waste_kwh, fc, ct_tax,
                            extra={
                                'cusum_trigger_date': str(trigger_date),
                                'baseline_daily_kwh': round(mu, 1),
                                'cusum_threshold':    round(H, 1),
                            }
                        )
                        print(f"  [S07] {asset_id}: CUSUM alarm {trigger_date} | "
                              f"baseline={mu:.0f} kWh/day | "
                              f"waste={waste_kwh:.0f} kWh | cost=NZD {fc}")
                else:
                    print(f"  [S07] {asset_id}: no degradation detected")

        # ── S10: NABERSNZ BENCHMARKING ─────────────────────────────────────
        # SKIP if data completeness < 95% — gaps understate YTD consumption
        # and produce false-low ratios (miss breaches) or false-high (wrong assets)
        if completeness < COMPLETENESS_THRESH:
            print(f"  [S10] {asset_id}: SKIPPED (completeness={completeness:.1%})")
        else:
            ytd_kwh       = df['total_power_kw'].sum() * 0.25
            ytd_mj        = ytd_kwh * KWH_TO_MJ
            days_elapsed  = max(
                (df['timestamp'].max() - df['timestamp'].min()).days, 1)
            total_cdd_ytd = df['cdd'].sum() * 0.25
            budget_mj     = (NABERSNZ_BASE_MJ + NABERSNZ_CDD_MULT * total_cdd_ytd) * area

            if budget_mj > 0:
                ratio = ytd_mj / budget_mj
                nabersnz_summary.append({
                    'asset_id':          asset_id,
                    'nabersnz_ratio':    round(ratio, 3),
                    'ytd_actual_mj_sqm': round(ytd_mj / area, 1),
                    'budget_mj_sqm':     round(budget_mj / area, 1),
                    'breach':            ratio > S10_OVERRUN_RATIO,
                })
                if ratio > S10_OVERRUN_RATIO:
                    overrun_kwh = (ytd_mj - budget_mj) / KWH_TO_MJ
                    fc, ct = calc_financial(overrun_kwh)
                    log_event(asset_id, 'S10', 'L1_NABERSNZ_BREACH',
                              df['timestamp'].min(), df['timestamp'].max(),
                              area, days_elapsed*24*60, assessed_mins,
                              overrun_kwh, fc, ct,
                              extra={
                                  'nabersnz_ratio':     round(ratio, 3),
                                  'ytd_actual_mj_sqm':  round(ytd_mj / area, 1),
                                  'nabersnz_budget_mj': round(budget_mj, 1),
                                  'days_elapsed':       days_elapsed,
                              })
                    print(f"  [S10] {asset_id}: BREACH ratio={ratio:.3f} | "
                          f"actual={ytd_mj/area:.1f} MJ/sqm | overrun={overrun_kwh:.1f} kWh")
                else:
                    print(f"  [S10] {asset_id}: on track ratio={ratio:.3f}")

    # ── Write output ──────────────────────────────────────────────────────────
    if audit_ledger:
        out_path = DATA_PATH / "energy_audit_log.csv"
        df_out   = pd.DataFrame(audit_ledger)
        df_out.to_csv(out_path, index=False)
        print(f"\nEnergy Audit complete — {len(audit_ledger)} events logged.")
        print(f"Output: {out_path}")
        print("\nSummary by scenario:")
        print(df_out.groupby('scenario')[['waste_kwh','financial_cost','carbon_kg']]
              .sum().round(2))
    else:
        print("\nEnergy Audit complete — no events detected.")
    if nabersnz_summary:
        pd.DataFrame(nabersnz_summary).to_csv(DATA_PATH / "nabersnz_summary.csv", index=False)
        print(f"NABERSNZ summary: {len(nabersnz_summary)} assets written")

if __name__ == "__main__":
    run_energy_audit()
