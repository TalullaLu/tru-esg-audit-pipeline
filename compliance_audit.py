# compliance_audit.py
# ESG Evidence & Compliance Engine — S02 | S09 | S11 | S12
# Covers: Invoice integrity, Billing variance, Travel class, Waste compliance

import pandas as pd
import numpy as np
from pathlib import Path
from registry import ASSET_SPACE_REGISTRY

pd.options.mode.chained_assignment = None

BASE_PATH = Path(__file__).resolve().parent
DATA_PATH = BASE_PATH / "data"

# ── Parameters ─────────────────────────────────────────────────────────────────
ELEC_RATE_NZD        = 0.25   # NZD/kWh (NZ assets)
ELEC_RATE_AUD        = 0.40   # AUD/kWh (AU assets — dim_esg_compliance_parameters)
EMISSION_FACTOR_NZ   = 0.11   # kgCO2e/kWh (MfE 2025)
EMISSION_FACTOR_AU   = 0.67   # kgCO2e/kWh (NGER 2024)

# S09 — Invoice vs. NABERS benchmark
NABERS_INTENSITY_MJ  = 265.0  # MJ/sqm/year — NABERS FY2020 median base building
KWH_TO_MJ            = 3.6
S09_VARIANCE_THRESH  = 0.15   # 15% — IPMVP Option C uncertainty band midpoint

# S11 — Travel class
S11_MAX_SHORT_HAUL_HRS = 6.0  # hours — TMC industry standard threshold

# S12 — Waste compliance
HAZARDOUS_TYPES      = {'Hazardous', 'E-Waste'}


def run_compliance_audit():
    print("=" * 60)
    print("ESG Evidence & Compliance Engine  —  S02 | S09 | S11 | S12")
    print("=" * 60)

    # ── Load data ──────────────────────────────────────────────────────────────
    try:
        invoices  = pd.read_csv(DATA_PATH / "dim_invoices_proxy.csv")
        travel    = pd.read_csv(DATA_PATH / "fact_travel_expense.csv")
        waste     = pd.read_csv(DATA_PATH / "fact_waste_manifest.csv")
        telemetry = pd.read_csv(DATA_PATH / "fact_telemetry_ledger.csv")
    except Exception as e:
        print(f"CRITICAL: Data load failure -> {e}")
        return

    # Strip whitespace from column names (defensive)
    travel.columns    = travel.columns.str.strip()
    invoices.columns  = invoices.columns.str.strip()
    waste.columns     = waste.columns.str.strip()

    telemetry['timestamp'] = pd.to_datetime(telemetry['timestamp'])

    audit_ledger = []

    def log_evidence(ref_id, asset_id, scenario, status, detail,
                     financial_exposure=0.0, carbon_kg=0.0, extra=None):
        record = {
            "ref_id":              ref_id,
            "asset_id":            asset_id,
            "scenario":            scenario,
            "status":              status,
            "detail":              detail,
            "financial_exposure":  round(float(financial_exposure), 2),
            "carbon_kg":           round(float(carbon_kg), 3),
        }
        if extra:
            record.update(extra)
        audit_ledger.append(record)

    # ── S02: INVOICE HASH INTEGRITY ────────────────────────────────────────────
    # Trigger: SHA-256 hash mismatch between uploaded PDF and original signature
    # Applied to: Asset_11 (Sydney) — only invoiced asset
    # Standard: ISO/IEC 27001:2022; ISAE 3000
    print("\n--- S02: Invoice Hash Integrity ---")

    s02_triggered_assets = set()  # track for S09 cascade suspension

    for _, row in invoices.iterrows():
        asset_id = row['asset_id']
        if pd.isna(row['uploaded_pdf_hash']) or pd.isna(row['original_crypto_signature']):
            log_evidence(
                asset_id, asset_id, 'S02', 'L1_HASH_MISSING',
                'Invoice hash field is null — evidence chain cannot be established',
                extra={'billing_month': row['billing_month']}
            )
            s02_triggered_assets.add(asset_id)
            print(f"  [S02] {asset_id}: hash field null — evidence chain broken")

        elif row['uploaded_pdf_hash'] != row['original_crypto_signature']:
            log_evidence(
                asset_id, asset_id, 'S02', 'L1_HASH_MISMATCH',
                f"PDF hash [{row['uploaded_pdf_hash']}] does not match "
                f"original signature [{row['original_crypto_signature']}] — "
                f"tampered or corrupted invoice",
                extra={'billing_month': row['billing_month']}
            )
            s02_triggered_assets.add(asset_id)
            print(f"  [S02] {asset_id}: HASH MISMATCH — invoice quarantined")

        else:
            print(f"  [S02] {asset_id}: hash verified ✓")

    # ── S09: INVOICE vs. NABERS BENCHMARK VARIANCE ─────────────────────────────
    # Trigger: |actual_billed_kwh - inferred_kwh| / inferred_kwh > 15%
    # inferred_kwh = area_sqm × NABERS_INTENSITY_MJ ÷ 3.6 ÷ 12
    # Applies to: Asset_11 (Sydney) — no IoT metering
    # Cascade: suspended if S02 triggered for same asset (ISAE 3000)
    # Standard: NABERS FY2020 median; IPMVP Option C
    print("\n--- S09: Invoice vs. NABERS Benchmark Variance ---")

    for _, row in invoices.iterrows():
        asset_id = row['asset_id']
        info     = ASSET_SPACE_REGISTRY.get(asset_id, {})

        # Only process AU assets without IoT (proxy billing only)
        if info.get('region') != 'AU' or info.get('has_iot', False):
            continue

        # Cascade suspension: if S02 fired on this asset, suspend S09
        if asset_id in s02_triggered_assets:
            log_evidence(
                asset_id, asset_id, 'S09', 'SUSPENDED_PENDING_S02',
                'S09 analysis suspended — upstream S02 hash breach unresolved. '
                'Billing data cannot be relied upon until invoice integrity is confirmed.',
                extra={'billing_month': row['billing_month']}
            )
            print(f"  [S09] {asset_id}: SUSPENDED — S02 hash breach unresolved")
            continue

        # Calculate inferred consumption from NABERS benchmark
        area_sqm      = info.get('area_sqm', 0.0)
        inferred_kwh  = (area_sqm * NABERS_INTENSITY_MJ / KWH_TO_MJ / 12)
        actual_kwh    = float(row['actual_billed_kwh'])
        variance      = abs(actual_kwh - inferred_kwh) / (inferred_kwh + 1e-6)

        if variance > S09_VARIANCE_THRESH:
            gap_kwh      = abs(actual_kwh - inferred_kwh)
            fin_exposure = round(gap_kwh * ELEC_RATE_AUD, 2)
            carbon_kg    = round(gap_kwh * EMISSION_FACTOR_AU, 3)
            log_evidence(
                asset_id, asset_id, 'S09', 'L4_BILLING_VARIANCE',
                f"Billed {actual_kwh:.0f} kWh vs NABERS-inferred {inferred_kwh:.0f} kWh "
                f"— variance {variance:.1%} exceeds 15% threshold",
                financial_exposure=fin_exposure,
                carbon_kg=carbon_kg,
                extra={
                    'actual_billed_kwh':  actual_kwh,
                    'inferred_kwh':       round(inferred_kwh, 1),
                    'variance_pct':       round(variance * 100, 1),
                    'billing_month':      row['billing_month'],
                }
            )
            print(f"  [S09] {asset_id}: variance={variance:.1%} | "
                  f"actual={actual_kwh:.0f} kWh vs inferred={inferred_kwh:.0f} kWh | "
                  f"exposure=AUD {fin_exposure}")
        else:
            print(f"  [S09] {asset_id}: variance={variance:.1%} — within threshold ✓")

    # ── S11: SCOPE 3 TRAVEL CLASS AUDIT ───────────────────────────────────────
    # Trigger: booked_class = 'Business' AND flight_hours < 6
    # Evidence: e-ticket fare basis code (simulated via booked_class field)
    # Standard: GHG Protocol Scope 3 Cat.6; ISO 14083:2023
    print("\n--- S11: Scope 3 Travel Class Audit ---")

    for _, row in travel.iterrows():
        flight_hours = float(row['flight_hours'])
        booked_class = str(row['booked_class']).strip()

        if booked_class == 'Business' and flight_hours < S11_MAX_SHORT_HAUL_HRS:
            log_evidence(
                str(row['ticket_id']), str(row['employee_id']),
                'S11', 'L3_TRAVEL_CLASS_AUDIT',
                f"Business class on short-haul route {row['route']} "
                f"({flight_hours:.1f} hrs) — exceeds 6-hour short-haul threshold",
                financial_exposure=float(row['ticket_price_aud']),
                extra={
                    'route':            row['route'],
                    'booked_class':     booked_class,
                    'flight_hours':     flight_hours,
                    'ticket_price_aud': float(row['ticket_price_aud']),
                    'employee_id':      row['employee_id'],
                }
            )
            print(f"  [S11] {row['employee_id']}: {row['route']} Business "
                  f"{flight_hours:.1f}hrs | AUD {row['ticket_price_aud']:,.0f} — FLAGGED")
        else:
            print(f"  [S11] {row['employee_id']}: {row['route']} {booked_class} "
                  f"{flight_hours:.1f}hrs — compliant ✓")

    # ── S12: HAZARDOUS WASTE DISPOSAL COMPLIANCE ───────────────────────────────
    # Trigger: waste_type IN ('Hazardous', 'E-Waste') AND disposal_cert_url IS NULL
    # Standard: GRI 306:2020; NZ HSNO Act 1996; Basel Convention
    print("\n--- S12: Hazardous Waste Disposal Compliance ---")

    for _, row in waste.iterrows():
        waste_type = str(row['waste_type']).strip()
        cert_url   = row['disposal_cert_url']
        cert_missing = pd.isna(cert_url) or str(cert_url).strip() == ''

        if waste_type in HAZARDOUS_TYPES and cert_missing:
            log_evidence(
                str(row['manifest_id']), str(row['asset_id']),
                'S12', 'L3_WASTE_CERT_MISSING',
                f"{waste_type} disposal record has no certificate URL — "
                f"compliance with HSNO Act 1996 and Basel Convention cannot be verified",
                extra={
                    'waste_type':     waste_type,
                    'disposal_date':  row['disposal_date'],
                    'quantity_kg':    float(row['quantity_kg']),
                }
            )
            print(f"  [S12] {row['asset_id']}: {waste_type} {row['quantity_kg']}kg "
                  f"— NO DISPOSAL CERTIFICATE")
        elif waste_type in HAZARDOUS_TYPES:
            print(f"  [S12] {row['asset_id']}: {waste_type} — certificate verified ✓")
        else:
            print(f"  [S12] {row['asset_id']}: {waste_type} — non-hazardous, no cert required")

    # ── S09-AU: Generate NABERS AU summary for dashboard ──────────────────────
    AU_BUDGET_MJ_SQM = 165.0  # NABERS Energy 5-star benchmark, Sydney CBD (indicative)
                               # Source: NABERS 2023 Technical Guidelines, Clean Energy Regulator
    AU_ASSET_ID      = 'Asset_11_AU_Sydney'
    au_info          = ASSET_SPACE_REGISTRY.get(AU_ASSET_ID, {})
    au_area_sqm      = au_info.get('area_sqm', 1000.0)

    if AU_ASSET_ID in s02_triggered_assets:
        # S02 triggered — suspend AU energy benchmark, output placeholder row
        au_inferred_kwh    = au_area_sqm * NABERS_INTENSITY_MJ / KWH_TO_MJ / 12
        au_inferred_mj_sqm = au_inferred_kwh * 12 * KWH_TO_MJ / au_area_sqm
        au_summary = pd.DataFrame([{
            'asset_id':           AU_ASSET_ID,
            'area_sqm':           au_area_sqm,
            'inferred_kwh_month': round(au_inferred_kwh, 1),
            'ytd_actual_mj_sqm':  round(au_inferred_mj_sqm, 1),
            'budget_mj_sqm':      AU_BUDGET_MJ_SQM,
            'nabers_ratio':       round(au_inferred_mj_sqm / AU_BUDGET_MJ_SQM, 3),
            'breach':             au_inferred_mj_sqm > AU_BUDGET_MJ_SQM * 1.10,
            'suspended':          True,
            'suspension_reason':  'S02_HASH_BREACH',
        }])
        print(f"\n  [AU Benchmark] {AU_ASSET_ID}: SUSPENDED — S02 hash breach. "
              f"Placeholder row written (inferred {au_inferred_mj_sqm:.1f} MJ/sqm).")
    else:
        # S02 clear — calculate from actual billed data
        au_invoices = invoices[invoices['asset_id'] == AU_ASSET_ID]
        if au_invoices.empty:
            print(f"\n  [AU Benchmark] {AU_ASSET_ID}: no invoice data found — skipping.")
            au_summary = None
        else:
            actual_kwh_month   = float(au_invoices['actual_billed_kwh'].mean())
            actual_mj_sqm      = actual_kwh_month * 12 * KWH_TO_MJ / au_area_sqm
            au_summary = pd.DataFrame([{
                'asset_id':           AU_ASSET_ID,
                'area_sqm':           au_area_sqm,
                'inferred_kwh_month': round(actual_kwh_month, 1),
                'ytd_actual_mj_sqm':  round(actual_mj_sqm, 1),
                'budget_mj_sqm':      AU_BUDGET_MJ_SQM,
                'nabers_ratio':       round(actual_mj_sqm / AU_BUDGET_MJ_SQM, 3),
                'breach':             actual_mj_sqm > AU_BUDGET_MJ_SQM * 1.10,
                'suspended':          False,
                'suspension_reason':  '',
            }])
            print(f"\n  [AU Benchmark] {AU_ASSET_ID}: actual {actual_mj_sqm:.1f} MJ/sqm "
                  f"vs budget {AU_BUDGET_MJ_SQM} — "
                  f"{'BREACH' if actual_mj_sqm > AU_BUDGET_MJ_SQM * 1.10 else 'within budget'}")

    if au_summary is not None:
        au_out = DATA_PATH / "nabers_au_summary.csv"
        au_summary.to_csv(au_out, index=False)
        print(f"  [AU Benchmark] Output: {au_out}")
        
    # ── Write output ───────────────────────────────────────────────────────────
    if audit_ledger:
        out_path = DATA_PATH / "esg_compliance_audit_log.csv"
        pd.DataFrame(audit_ledger).to_csv(out_path, index=False)
        print(f"\nCompliance Audit complete — {len(audit_ledger)} events logged.")
        print(f"Output: {out_path}")
        print("\nSummary by scenario:")
        df_out = pd.DataFrame(audit_ledger)
        print(df_out.groupby('scenario')[['financial_exposure','carbon_kg']].sum().round(2))
    else:
        print("\nCompliance Audit complete — no events detected.")


if __name__ == "__main__":
    run_compliance_audit()