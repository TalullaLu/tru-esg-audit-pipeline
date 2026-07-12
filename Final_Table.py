# Final_Table.py
# Generates star schema tables for TRU-ESG Streamlit dashboard
# Outputs: fact_audit_events, dim_assets, dim_scenarios, dim_kpi_summary, dim_priority_actions

import pandas as pd
import numpy as np
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
DATA_PATH = BASE_PATH / "data"

# ── Department mapping ─────────────────────────────────────────────────────────
DEPT_MAP = {
    'S01': 'IT / Data',
    'S02': 'Finance / Legal',
    'S03': 'IT / Data',
    'S04': 'Facilities',
    'S05': 'Facilities',
    'S06': 'Facilities',
    'S07': 'Facilities',
    'S08': 'Facilities',
    'S09': 'Finance / Legal',
    'S10': 'Energy Compliance',
    'S11': 'ESG / Compliance',
    'S12': 'ESG / Compliance',
}

# ── Scenario metadata ──────────────────────────────────────────────────────────
SCENARIO_META = {
    'S01': ('Unauthorised Device Detection',       'IT / Data',        'Group 1 — Data Integrity', 'L0', 'IoT & Facility', 'ISA/IEC 62443-2-1 · ISO/IEC 27402:2023'),
    'S02': ('Invoice Hash Integrity',              'Finance / Legal',  'Group 1 — Data Integrity', 'L1', 'ESG Evidence',   'ISO/IEC 27001:2022 · ISAE 3000'),
    'S03': ('Telemetry Data Gap',                  'IT / Data',        'Group 1 — Data Integrity', 'L1', 'IoT & Facility', 'ISO 50001:2018 · IPMVP EVO 10000-1:2022'),
    'S04': ('Sub-Meter Calibration Drift',         'Facilities',       'Group 2 — Energy',         'L2', 'Energy',         'LEED v4.1 Advanced Energy Metering'),
    'S05': ('After-Hours HVAC Idle Running',       'Facilities',       'Group 2 — Energy',         'L2', 'Energy',         'ASHRAE Guideline 14-2023 · ISO 50001:2018'),
    'S06': ('IEQ Greenwashing Detection',          'Facilities',       'Group 3 — IEQ',            'L1', 'IoT & Facility', 'NZS 4303:1990'),
    'S07': ('Equipment Efficiency Degradation',    'Facilities',       'Group 2 — Energy',         'L2', 'Energy',         'ISO 50001:2018 · DOE/LBNL EMIS'),
    'S08': ('High-Demand Zone IEQ Optimisation',   'Facilities',       'Group 3 — IEQ',            'L2', 'IoT & Facility', 'WELL Building Standard v2'),
    'S09': ('Invoice vs. NABERS Benchmark',        'Finance / Legal',  'Group 4 — Evidence',       'L4', 'ESG Evidence',   'IPMVP Option C · ISAE 3000'),
    'S10': ('NABERSNZ Benchmarking Compliance',    'Energy Compliance','Group 2 — Energy',         'L1', 'Energy',         'NABERSNZ Rules v1.2 · AS/NZS 3598.1:2014'),
    'S11': ('Scope 3 Travel Class Audit',          'ESG / Compliance', 'Group 5 — Scope 3',        'L3', 'ESG Evidence',   'GHG Protocol Scope 3 Cat.6 · ISO 14083:2023'),
    'S12': ('Hazardous Waste Disposal Compliance', 'ESG / Compliance', 'Group 5 — Scope 3',        'L3', 'ESG Evidence',   'HSNO Act 1996 · Basel Convention · GRI 306:2020'),
}

# CEO-visible scenario groups for Top 3 Priority Actions
CEO_SCENARIOS = {
    'legal_reputational':       ['S02', 'S09', 'S12'],
    'financial_operational':    ['S07', 'S08', 'S10'],
    'regulatory_certification': ['S06', 'S11'],
}


def run():
    print("=" * 60)
    print("Final Table Generator — Star Schema")
    print("=" * 60)

    # ── Load audit logs ────────────────────────────────────────────────────────
    fac  = pd.read_csv(DATA_PATH / "facility_audit_log.csv")
    eng  = pd.read_csv(DATA_PATH / "energy_audit_log.csv")
    comp = pd.read_csv(DATA_PATH / "esg_compliance_audit_log.csv")

    # Normalise timestamps
    fac['event_time']  = pd.to_datetime(fac['start_time'])
    eng['event_time']  = pd.to_datetime(eng['timestamp'])
    if 'disposal_date' in comp.columns:
        comp['event_time'] = pd.to_datetime(comp['disposal_date'], errors='coerce')
    else:
        comp['event_time'] = pd.Timestamp('2025-11-01')
    comp['event_time'] = comp['event_time'].fillna(pd.Timestamp('2025-11-01'))

    # ── Build fact_audit_events ────────────────────────────────────────────────
    def build_fact(df, category):
        rows = []
        for i, row in df.iterrows():
            rows.append({
                'asset_id':             row.get('asset_id', 'Unknown'),
                'scenario':             row['scenario'],
                'status':               row['status'],
                'category':             category,
                'department':           DEPT_MAP.get(row['scenario'], 'Unknown'),
                'event_time':           row.get('event_time', pd.NaT),
                'anomaly_duration_mins':float(row.get('anomaly_duration_mins', 0) or 0),
                'waste_kwh':            float(row.get('waste_kwh', 0) or 0),
                'financial_cost':       float(row.get('financial_cost', 0) or 0),
                'financial_exposure':   float(row.get('financial_exposure', 0) or 0),
                'carbon_kg':            float(row.get('carbon_kg', 0) or 0),
                'cognitive_loss_nzd':   float(row.get('cognitive_loss_nzd', 0) or 0),
                'peak_co2_ppm':         float(row.get('peak_co2_ppm', 0) or 0),
                'nabersnz_ratio':       float(row.get('nabersnz_ratio', 0) or 0),
                'detail':               str(row.get('detail', row.get('recommendation', ''))),
            })
        return pd.DataFrame(rows)

    fact = pd.concat([
        build_fact(fac,  'Facility'),
        build_fact(eng,  'Energy'),
        build_fact(comp, 'Compliance'),
    ], ignore_index=True)

    fact['event_id'] = [f"EVT_{i+1:04d}" for i in range(len(fact))]
    fact['region']   = fact['asset_id'].apply(
        lambda x: 'AU' if ('Sydney' in str(x) or '_AU_' in str(x)) else 'NZ'
    )

    fact.to_csv(DATA_PATH / "fact_audit_events.csv", index=False)
    print(f"  fact_audit_events.csv: {len(fact)} rows")

    # ── Build dim_assets ───────────────────────────────────────────────────────
    import sys
    sys.path.insert(0, str(BASE_PATH))
    from registry import ASSET_SPACE_REGISTRY

    dim_assets = pd.DataFrame([
        {
            'asset_id':          aid,
            'region':            info.get('region', 'NZ'),
            'location':          info.get('location', ''),
            'area_sqm':          info.get('area_sqm', 0),
            'occupant_count':    info.get('occupant_count', 0),
            'space_designation': info.get('space_designation', 'STANDARD'),
            'display_name':      info.get('display_name', aid),
            'has_iot':           info.get('has_iot', False),
        }
        for aid, info in ASSET_SPACE_REGISTRY.items()
    ])
    dim_assets.to_csv(DATA_PATH / "dim_assets.csv", index=False)
    print(f"  dim_assets.csv: {len(dim_assets)} rows")

    # ── Build dim_scenarios ────────────────────────────────────────────────────
    dim_scenarios = pd.DataFrame([
        {
            'scenario':       sid,
            'scenario_name':  name,
            'department':     dept,
            'audit_group':    group,
            'severity_level': level,
            'engine':         engine,
            'standard':       standard,
            'ceo_visible':    sid not in ['S01', 'S03', 'S04', 'S05'],
        }
        for sid, (name, dept, group, level, engine, standard) in SCENARIO_META.items()
    ])
    dim_scenarios.to_csv(DATA_PATH / "dim_scenarios.csv", index=False)
    print(f"  dim_scenarios.csv: {len(dim_scenarios)} rows")

    # ── Build dim_kpi_summary ──────────────────────────────────────────────────
    # Total violations: evidence-chain scenarios only (per design)
    violation_scenarios = ['S01', 'S02', 'S03', 'S11', 'S12']
    total_violations = len(fact[fact['scenario'].isin(violation_scenarios)])

    # ── Avoidable cost / carbon (NZ) with S10 double-count protection ─────────
    # Layer 1: attributable waste (S04 + S05 + S07) — direct causes
    # Layer 2: S10 net overrun = S10 overrun − already-attributed waste
    #          (same asset). Prevents counting the same kWh twice.

    attributable = fact[
        (fact['scenario'].isin(['S04', 'S05', 'S07'])) &
        (fact['region'] == 'NZ')
    ]
    attributable_cost   = attributable['financial_cost'].sum()
    attributable_carbon = attributable['carbon_kg'].sum()

    s10_rows = fact[(fact['scenario'] == 'S10') & (fact['region'] == 'NZ')]
    s10_net_cost   = 0.0
    s10_net_carbon = 0.0
    for _, s10_row in s10_rows.iterrows():
        asset = s10_row['asset_id']
        # kWh already explained by S04/S05/S07 on the SAME asset
        explained_kwh = attributable[
            attributable['asset_id'] == asset
        ]['waste_kwh'].sum()
        net_kwh = max(s10_row['waste_kwh'] - explained_kwh, 0.0)
        # Recalculate cost/carbon on the net (unexplained) portion only
        if s10_row['waste_kwh'] > 0:
            ratio = net_kwh / s10_row['waste_kwh']
            s10_net_cost   += s10_row['financial_cost'] * ratio
            s10_net_carbon += s10_row['carbon_kg'] * ratio

    nz_cost   = attributable_cost + s10_net_cost
    nz_carbon = attributable_carbon + s10_net_carbon

    # AU (S09 — suspended pending S02, so likely zero)
    au_cost   = fact[fact['scenario'] == 'S09']['financial_exposure'].sum()
    au_carbon = fact[fact['scenario'] == 'S09']['carbon_kg'].sum()

    # S08 staff productivity loss
    s08_loss = fact[fact['scenario'] == 'S08']['cognitive_loss_nzd'].sum()

    au_note = 'Under Review — pending invoice verification' if au_cost == 0 else ''

    kpi = pd.DataFrame([
        {'metric': 'total_violations',    'value_nzd': total_violations,    'value_aud': 0,
         'label': 'Data & Compliance Violations',           'unit': 'count',  'note': ''},
        {'metric': 'avoidable_cost_nz',   'value_nzd': round(nz_cost, 2),   'value_aud': 0,
         'label': 'Avoidable Energy Cost (NZ)',             'unit': 'NZD',    'note': ''},
        {'metric': 'avoidable_cost_au',   'value_nzd': 0,                   'value_aud': round(au_cost, 2),
         'label': 'Avoidable Energy Cost (AU)',             'unit': 'AUD',    'note': au_note},
        {'metric': 'avoidable_carbon_nz', 'value_nzd': round(nz_carbon, 1), 'value_aud': 0,
         'label': 'Avoidable Carbon Emissions (NZ)',        'unit': 'kgCO2e', 'note': ''},
        {'metric': 'avoidable_carbon_au', 'value_nzd': 0,                   'value_aud': round(au_carbon, 1),
         'label': 'Avoidable Carbon Emissions (AU)',        'unit': 'kgCO2e', 'note': au_note},
        {'metric': 's08_productivity_loss','value_nzd': round(s08_loss, 2), 'value_aud': 0,
         'label': 'HIGH-DEMAND Zone Staff Productivity Loss','unit': 'NZD',   'note': 'Zero-cost remedy available'},
    ])
    kpi.to_csv(DATA_PATH / "dim_kpi_summary.csv", index=False)
    print(f"  dim_kpi_summary.csv: {len(kpi)} rows")
    print(f"    NZ avoidable cost:   NZD {nz_cost:,.2f} "
          f"(attributable {attributable_cost:,.2f} + S10 net {s10_net_cost:,.2f})")
    print(f"    NZ avoidable carbon: {nz_carbon:,.1f} kgCO2e")

    # ── Build dim_priority_actions ─────────────────────────────────────────────
    def get_top(scenario_list, sort_col):
        subset = fact[fact['scenario'].isin(scenario_list)].copy()
        if subset.empty:
            return None
        return subset.nlargest(1, sort_col).iloc[0]

    p1 = get_top(CEO_SCENARIOS['legal_reputational'],       'financial_exposure')
    p2 = get_top(CEO_SCENARIOS['financial_operational'],    'financial_cost')
    p3 = get_top(CEO_SCENARIOS['regulatory_certification'], 'anomaly_duration_mins')

    def generate_detail(row):
        """Auto-generate a description if the source detail is missing."""
        if row is None:
            return ''
        s = row['scenario']
        if s == 'S10':
            return (f"{row['asset_id']} YTD energy intensity is "
                    f"{(row['nabersnz_ratio'] - 1) * 100:.1f}% above its climate-adjusted "
                    f"NABERSNZ budget (ratio {row['nabersnz_ratio']:.3f}). "
                    f"Current rating at risk of downgrade at next annual assessment. "
                    f"Primary driver: sustained high IT load. Recommended: workload "
                    f"migration assessment or data centre exclusion application to NZGBC.")
        if s == 'S06':
            s06_events = fact[fact['scenario'] == 'S06']
            total_mins = s06_events['anomaly_duration_mins'].sum()
            return (f"{row['asset_id']} recorded {len(s06_events)} sustained CO2 "
                    f"exceedance events above 1,000 ppm during November workdays "
                    f"(total {total_mins:.0f} minutes), breaching NZS 4303:1990 "
                    f"ventilation requirements.")
        if s == 'S08':
            s08_events = fact[fact['scenario'] == 'S08']
            total_loss = s08_events['cognitive_loss_nzd'].sum()
            return (f"{row['asset_id']} HIGH-DEMAND zone recorded "
                    f"{len(s08_events)} IEQ gap events in November. Estimated staff "
                    f"productivity loss: NZD {total_loss:,.0f}. Recoverable through HVAC "
                    f"fresh air recalibration within authorised +20% energy budget.")
        existing = str(row.get('detail', '')).strip()
        if existing and existing.lower() != 'nan':
            return existing
        return f"{row['status']} detected at {row['asset_id']}"

    priority = []
    for i, (label, row) in enumerate([
        ('Legal & Reputational Risk',       p1),
        ('Financial & Operational Impact',  p2),
        ('Regulatory & Certification Risk', p3),
    ], 1):
        if row is not None:
            name = SCENARIO_META.get(row['scenario'], ('',))[0]
            priority.append({
                'priority':                i,
                'dimension':               label,
                'scenario':                row['scenario'],
                'asset_id':                row['asset_id'],
                'finding':                 f"{name} — {row['status']}",
                'detail':                  generate_detail(row),
                'editable_recommendation': '',
            })

    pd.DataFrame(priority).to_csv(DATA_PATH / "dim_priority_actions.csv", index=False)
    print(f"  dim_priority_actions.csv: {len(priority)} rows")

    print("\nAll tables generated successfully.")
    print("\nSummary:")
    print(fact.groupby(['category', 'scenario'])['event_id'].count())


if __name__ == "__main__":
    run()
