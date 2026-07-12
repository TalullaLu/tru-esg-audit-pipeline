# app.py — TRU-ESG Audit Dashboard
# Page 1: Executive Dashboard (bordered colour cards + MoM deltas)
# Run: streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import altair as alt

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TRU-ESG Audit Dashboard",
    page_icon="🌿",
    layout="wide",
)
# ── Global CSS overrides ───────────────────────────────────────────────────────
st.markdown("""
<style>
    div[data-testid="stCaptionContainer"] p,
    .st-emotion-cache-1rp5jhn p,
    .st-emotion-cache-1rp5jhn {
        color: #2D3748 !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

DATA_PATH = Path(__file__).resolve().parent / "data"

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    fact      = pd.read_csv(DATA_PATH / "fact_audit_events.csv")
    assets    = pd.read_csv(DATA_PATH / "dim_assets.csv")
    scenarios = pd.read_csv(DATA_PATH / "dim_scenarios.csv")
    kpi       = pd.read_csv(DATA_PATH / "dim_kpi_summary.csv")
    priority  = pd.read_csv(DATA_PATH / "dim_priority_actions.csv")
    try:
        prior = pd.read_csv(DATA_PATH / "dim_baseline_prior_month.csv")
    except Exception:
        prior = pd.DataFrame(columns=['metric', 'prior_value', 'label'])
    fact['event_time'] = pd.to_datetime(fact['event_time'], errors='coerce')
    return fact, assets, scenarios, kpi, priority, prior

fact, assets, scenarios, kpi, priority, prior = load_data()

# ── User-facing name mappings (no internal codes in UI) ────────────────────────
SCEN_NAME = dict(zip(scenarios['scenario'], scenarios['scenario_name']))
if 'standard' in scenarios.columns:
    SCEN_STD = dict(zip(scenarios['scenario'], scenarios['standard']))
else:
    SCEN_STD = {}

if 'display_name' in assets.columns:
    ASSET_NAME = dict(zip(assets['asset_id'], assets['display_name']))
else:
    ASSET_NAME = {}

def display_asset(aid):
    """User-facing site name; falls back to shortened id."""
    return ASSET_NAME.get(aid, str(aid))

def display_scenario(sid):
    return SCEN_NAME.get(sid, str(sid))

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("TRU-ESG Audit Dashboard")
st.caption("Multi-Jurisdictional ESG Assurance  ·  New Zealand & Australia  ·  November 2025")

tab1, tab2, tab3, tab4 = st.tabs([
    "  Executive Dashboard  ",
    "  IEQ Intelligence  ",
    "  Energy Performance  ",
    "  Evidence & Scope 3  ",
])

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — EXECUTIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    st.subheader("Key Indicators — November 2025")
    st.caption("Six indicators covering evidence integrity, avoidable cost, "
               "carbon reduction potential, and workplace productivity. "
               "Deltas compare against October 2025.")

    # ── KPI card builder (custom HTML, bordered, coloured) ────────────────────
    def kpi_value(metric):
        row = kpi[kpi['metric'] == metric].iloc[0]
        return row

    def prior_value(metric):
        row = prior[prior['metric'] == metric]
        if row.empty:
            return None
        return float(row.iloc[0]['prior_value'])

    def delta_html(current, previous):
        """Lower is better for every KPI. Red ▲ worse, green ▼ better."""
        if previous is None or previous == 0:
            return "<span style='color:#8A8F98;font-size:13px;'>No prior-month comparison</span>"
        pct = (current - previous) / previous * 100
        if pct > 0:
            return (f"<span style='color:#C0392B;font-size:14px;font-weight:600;'>"
                    f"▲ +{pct:.1f}% vs last month</span>")
        elif pct < 0:
            return (f"<span style='color:#1E8449;font-size:14px;font-weight:600;'>"
                    f"▼ {pct:.1f}% vs last month</span>")
        return "<span style='color:#8A8F98;font-size:14px;'>— unchanged</span>"

    def card(col, label, value_str, delta, caption, accent):
        with col:
            st.markdown(f"""
<div style="
    border: 1.5px solid #4A5568;
    border-radius: 0;
    padding: 16px 18px 14px 18px;
    background: #FFFFFF;
    margin: 0 8px 18px 8px;
    height: 180px;
    overflow: hidden;">
  <div style="font-size:13px; font-weight:600; color:#5B6472;
              text-transform:uppercase; letter-spacing:0.4px;">{label}</div>
  <div style="font-size:34px; font-weight:700; color:{accent};
              margin:6px 0 4px 0;">{value_str}</div>
  <div style="margin-bottom:8px;">{delta}</div>
  <div style="font-size:12.5px; color:#6B7280; line-height:1.45;">{caption}</div>
</div>""", unsafe_allow_html=True)

    # Colours
    RED    = "#C0392B"   # violations
    BLUE   = "#1F5FA8"   # avoidable energy & carbon
    PURPLE = "#6C3483"   # staff productivity

    r1c1, r1c2, r1c3 = st.columns(3)
    r2c1, r2c2, r2c3 = st.columns(3)

    # Card 1 — Violations
    row = kpi_value('total_violations')
    card(r1c1,
         row['label'],
         f"{int(row['value_nzd'])}",
         delta_html(row['value_nzd'], prior_value('total_violations')),
         "Unauthorised devices, offline sensors, failed document verification, "
         "travel and waste non-compliance.",
         RED)

    # Card 2 — Avoidable cost NZ
    row = kpi_value('avoidable_cost_nz')
    card(r1c2,
         row['label'],
         f"NZD {row['value_nzd']:,.0f}",
         delta_html(row['value_nzd'], prior_value('avoidable_cost_nz')),
         "Energy waste identified by sub-meter, after-hours, degradation and "
         "benchmark audits. Double-counting eliminated at asset level.",
         BLUE)

    # Card 3 — Avoidable cost AU (under review)
    row = kpi_value('avoidable_cost_au')
    if pd.notna(row['note']) and row['note']:
        card(r1c3, row['label'], "Under Review",
             "<span style='color:#8A8F98;font-size:13px;'>Comparison unavailable</span>",
             row['note'], BLUE)
    else:
        card(r1c3, row['label'], f"AUD {row['value_aud']:,.0f}",
             delta_html(row['value_aud'], prior_value('avoidable_cost_au')),
             "Billing variance identified against NABERS benchmark.", BLUE)

    # Card 4 — Carbon NZ
    row = kpi_value('avoidable_carbon_nz')
    card(r2c1,
         row['label'],
         f"{row['value_nzd']:,.0f} kgCO₂e",
         delta_html(row['value_nzd'], prior_value('avoidable_carbon_nz')),
         "Emissions eliminated if identified energy waste is remediated. "
         "Calculated at 0.11 kgCO₂e/kWh (MfE 2025).",
         BLUE)

    # Card 5 — Carbon AU
    row = kpi_value('avoidable_carbon_au')
    if pd.notna(row['note']) and row['note']:
        card(r2c2, row['label'], "Under Review",
             "<span style='color:#8A8F98;font-size:13px;'>Comparison unavailable</span>",
             row['note'], BLUE)
    else:
        card(r2c2, row['label'], f"{row['value_aud']:,.0f} kgCO₂e",
             delta_html(row['value_aud'], prior_value('avoidable_carbon_au')),
             "Emissions from billing variance at Sydney office.", BLUE)

    # Card 6 — Productivity loss
    row = kpi_value('s08_productivity_loss')
    card(r2c3,
         row['label'],
         f"NZD {row['value_nzd']:,.0f}",
         delta_html(row['value_nzd'], prior_value('s08_productivity_loss')),
         f"{row['note']} — HVAC fresh air recalibration within authorised "
         "energy budget.",
         PURPLE)

    st.divider()

    # ── Compliance matrix ──────────────────────────────────────────────────────
    st.subheader("Compliance Matrix — by Facility and Responsible Department")
    st.caption("Red indicates at least one audit finding requiring action. "
               "Green indicates no issues detected. Select a department and "
               "asset below the table to view underlying events.")

    DEPTS = ['Facilities', 'Energy Compliance', 'IT / Data',
             'Finance / Legal', 'ESG / Compliance']

    findings = fact.groupby(['asset_id', 'department']).size().reset_index(name='n')
    finding_set = set(zip(findings['asset_id'], findings['department']))

    nz_assets = assets[assets['region'] == 'NZ']['asset_id'].tolist()
    au_assets = assets[assets['region'] == 'AU']['asset_id'].tolist()

    def short_name(aid):
        return (aid.replace('Asset_', 'A')
                   .replace('_NZ_Boundary', '')
                   .replace('_AU_Sydney', ' SYD'))

    RED_DOT   = ('<span style="display:inline-block;width:10px;height:10px;'
                 'border-radius:50%;background:#E74C3C;"></span>')
    GREEN_DOT = ('<span style="display:inline-block;width:10px;height:10px;'
                 'border-radius:50%;background:#2ECC71;"></span>')

    def build_matrix_html(asset_list, dept_list=None):
        if dept_list is None:
            dept_list = DEPTS
        header = ('<tr><th style="text-align:left;padding:8px 12px;'
                  'border-bottom:2px solid #4A5568;">Department</th>')
        for aid in asset_list:
            header += (f'<th style="text-align:center;padding:8px 8px;'
                       f'border-bottom:2px solid #4A5568;font-size:12px;">'
                       f'{display_asset(aid)}</th>')
        header += '</tr>'

        body = ''
        for i, dept in enumerate(dept_list):
            bg = '#F7F9FB' if i % 2 == 0 else '#FFFFFF'
            body += f'<tr style="background:{bg};">'
            body += (f'<td style="padding:8px 12px;font-size:14px;'
                     f'border-bottom:1px solid #E2E8F0;">{dept}</td>')
            for aid in asset_list:
                dot = RED_DOT if (aid, dept) in finding_set else GREEN_DOT
                body += (f'<td style="text-align:center;padding:8px 8px;'
                         f'border-bottom:1px solid #E2E8F0;">{dot}</td>')
            body += '</tr>'

        return (f'<table style="width:100%;border-collapse:collapse;">'
                f'{header}{body}</table>')

    st.markdown("**New Zealand — Auckland**")
    st.markdown(build_matrix_html(nz_assets), unsafe_allow_html=True)
    st.markdown("")

    AU_DEPTS = ['Energy Compliance', 'Finance / Legal', 'ESG / Compliance']

    GREY_DOT = ('<span style="display:inline-block;width:10px;height:10px;'
                'border-radius:50%;background:#A0ADB8;"></span>')

    def build_au_matrix_html(asset_list):
        header = ('<tr><th style="text-align:left;padding:8px 12px;'
                  'border-bottom:2px solid #4A5568;">Department</th>')
        for aid in asset_list:
            header += (f'<th style="text-align:center;padding:8px 8px;'
                       f'border-bottom:2px solid #4A5568;font-size:12px;">'
                       f'{display_asset(aid)}</th>')
        header += '</tr>'

        body = ''
        for i, dept in enumerate(AU_DEPTS):
            bg = '#F7F9FB' if i % 2 == 0 else '#FFFFFF'
            body += f'<tr style="background:{bg};">'
            body += (f'<td style="padding:8px 12px;font-size:14px;'
                     f'border-bottom:1px solid #E2E8F0;">{dept}</td>')
            for aid in asset_list:
                if dept == 'Energy Compliance':
                    cell = (f'<td style="text-align:center;padding:8px 8px;'
                            f'border-bottom:1px solid #E2E8F0;font-size:11px;'
                            f'color:#7D6608;">⚠ To Verify</td>')
                else:
                    dot = RED_DOT if (aid, dept) in finding_set else GREEN_DOT
                    cell = (f'<td style="text-align:center;padding:8px 8px;'
                            f'border-bottom:1px solid #E2E8F0;">{dot}</td>')
                body += cell
            body += '</tr>'

        return (f'<table style="width:100%;border-collapse:collapse;">'
                f'{header}{body}</table>')

    st.markdown("**Australia — Sydney**")
    st.markdown(build_au_matrix_html(au_assets), unsafe_allow_html=True)
    st.caption("Sydney Office has no IoT sensors or sub-metering. "
               "Facility and IT/Data readings are unavailable. "
               "Energy billing is under document integrity review (S02).")

    # ── Drill-down selector ────────────────────────────────────────────────────
    st.markdown("**View underlying events**")
    col_a, col_b = st.columns(2)
    with col_a:
        sel_dept = st.selectbox("Department", DEPTS)
    with col_b:
        all_assets = nz_assets + au_assets
        sel_asset = st.selectbox("Asset", all_assets, format_func=display_asset)

    drill = fact[
        (fact['department'] == sel_dept) &
        (fact['asset_id'] == sel_asset)
    ]

    if drill.empty:
        st.success(f"No findings for {display_asset(sel_asset)} under {sel_dept}.")
    else:
        st.warning(f"{len(drill)} finding(s) for {display_asset(sel_asset)} "
                   f"under {sel_dept}:")
        drill = drill.copy()
        drill['Audit Check'] = drill['scenario'].map(display_scenario)
        display_cols = ['event_id', 'Audit Check', 'event_time',
                        'anomaly_duration_mins', 'financial_cost',
                        'financial_exposure', 'carbon_kg', 'detail']
        st.dataframe(
            drill[display_cols].sort_values('event_time'),
            width='stretch', hide_index=True,
        )

    st.divider()

    # ── Top 3 Priority Actions ─────────────────────────────────────────────────
    st.subheader("Priority Actions — Top 3")
    st.caption("The single most significant finding in each of three risk "
               "dimensions. System-recommended; recommendations editable "
               "by the audit team.")

    DIM_COLORS = {1: RED, 2: BLUE, 3: PURPLE}

    for _, p in priority.iterrows():
        accent = DIM_COLORS.get(int(p['priority']), BLUE)
        with st.container(border=True):
            pc1, pc2 = st.columns([1, 5])
            with pc1:
                st.markdown(
                    f"<div style='font-size:40px;font-weight:700;color:{accent};'>"
                    f"{int(p['priority'])}</div>"
                    f"<div style='font-size:12.5px;color:#5B6472;'>{p['dimension']}</div>",
                    unsafe_allow_html=True)
            with pc2:
                st.markdown(f"**{p['finding']}**")
                st.markdown(f"Asset: `{p['asset_id']}`")
                st.write(p['detail'])
                rec_raw = p.get('editable_recommendation')
                rec_val = '' if pd.isna(rec_raw) else str(rec_raw)
                st.text_input(
                    "Recommendation (editable)",
                    value=rec_val,
                    key=f"rec_{p['priority']}",
                    placeholder="Add audit team recommendation…",
                )

# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — IEQ INTELLIGENCE (audience: Facilities)
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Indoor Environment Quality — Facilities View")
    st.caption("Two layers of IEQ oversight: regulatory ventilation compliance "
               "(NZS 4303:1990) and high-demand zone optimisation "
               "(enhanced 800 ppm target). Working hours defined as 07:00–20:00, "
               "22 workdays in November.")

    import altair as alt

    # ── Layer 1: S06 Compliance (Asset_02) ─────────────────────────────────────
    st.markdown("#### Layer 1 — Ventilation Compliance")
    st.caption("CO₂ exceeded 1,000 ppm — a breach of NZS 4303:1990 ventilation "
               "requirements. Denominator: 286 working hours (22 workdays × 13 hours).")

    s06 = fact[fact['scenario'] == 'S06'].copy()

    WORKING_HOURS_MONTH = 286  # 22 workdays × 13 hours (07:00-20:00)

    if not s06.empty:
        for asset in s06['asset_id'].unique():
            asset_s06 = s06[s06['asset_id'] == asset]
            breach_hours = asset_s06['anomaly_duration_mins'].sum() / 60
            compliant_hours = WORKING_HOURS_MONTH - breach_hours
            breach_pct = breach_hours / WORKING_HOURS_MONTH * 100

            st.markdown(f"**{display_asset(asset)}** — {WORKING_HOURS_MONTH} total working hours in November")

            # Stacked horizontal bar: compliant (green) + breach (red)
            stack_df = pd.DataFrame({
                'Asset':  [display_asset(asset), display_asset(asset)],
                'Status': ['Compliant', 'Exceedance'],
                'Hours':  [compliant_hours, breach_hours],
            })
            chart = alt.Chart(stack_df).mark_bar(height=32).encode(
                x=alt.X('Hours:Q', title=None, axis=None,
                        scale=alt.Scale(domain=[0, WORKING_HOURS_MONTH])),
                y=alt.Y('Asset:N', title='', axis=None),
                color=alt.Color('Status:N',
                    scale=alt.Scale(domain=['Compliant', 'Exceedance'],
                                    range=['#1E8449', '#C0392B']),
                    legend=alt.Legend(title=None, orient='top')),
                order=alt.Order('Status:N', sort='descending'),
                tooltip=['Status', alt.Tooltip('Hours:Q', format='.1f')],
            ).properties(height=90)
            st.altair_chart(chart, use_container_width=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("Exceedance Hours", f"{breach_hours:.1f} h")
            m2.metric("Breach Rate", f"{breach_pct:.1f}%")
            m3.metric("Events", f"{len(asset_s06)}")
    else:
        st.success("No S06 ventilation breaches detected.")

    st.divider()

    # ── Layer 2: S08 High-Demand Optimisation (Asset_09) ───────────────────────
    st.markdown("#### Layer 2 — High-Demand Zone Air Quality")
    st.caption("Designated HIGH_DEMAND zone where CO₂ exceeded the enhanced "
               "800 ppm target. Each exceedance day and its total duration is "
               "shown below.")

    s08 = fact[fact['scenario'] == 'S08'].copy()

    if not s08.empty:
        # Stacked compliance bar for the HIGH_DEMAND zone
        s08_asset = s08['asset_id'].iloc[0]
        s08_breach_hours = s08['anomaly_duration_mins'].sum() / 60
        s08_compliant_hours = WORKING_HOURS_MONTH - s08_breach_hours

        st.markdown(f"**{display_asset(s08_asset)}** — {WORKING_HOURS_MONTH} total working hours in November (800 ppm enhanced target)")

        s08_stack = pd.DataFrame({
            'Asset':  [display_asset(s08_asset), display_asset(s08_asset)],
            'Status': ['Within Target', 'Above 800 ppm'],
            'Hours':  [s08_compliant_hours, s08_breach_hours],
        })
        s08_chart = alt.Chart(s08_stack).mark_bar(height=32).encode(
            x=alt.X('Hours:Q', title=None, axis=None,
                    scale=alt.Scale(domain=[0, WORKING_HOURS_MONTH])),
            y=alt.Y('Asset:N', title='', axis=None),
            color=alt.Color('Status:N',
                scale=alt.Scale(domain=['Within Target', 'Above 800 ppm'],
                                range=['#1E8449', '#6C3483']),
                legend=alt.Legend(title=None, orient='top')),
            order=alt.Order('Status:N', sort='descending'),
            tooltip=['Status', alt.Tooltip('Hours:Q', format='.1f')],
        ).properties(height=90)
        st.altair_chart(s08_chart, use_container_width=True)

        s08['date'] = s08['event_time'].dt.date
        daily = s08.groupby('date').agg(
            exceedance_hours=('anomaly_duration_mins', lambda x: x.sum() / 60),
            peak_co2=('peak_co2_ppm', 'max'),
            events=('event_id', 'count'),
        ).reset_index()
        daily['exceedance_hours'] = daily['exceedance_hours'].round(2)
        daily['peak_co2'] = daily['peak_co2'].astype(int)

        # Metrics row below the bar (same layout as S06)
        total_hours = daily['exceedance_hours'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Exceedance Hours", f"{total_hours:.1f} h")
        m2.metric("Breach Rate", f"{total_hours / WORKING_HOURS_MONTH * 100:.1f}%")
        m3.metric("Peak CO₂", f"{daily['peak_co2'].max()} ppm")

        st.info("Enhanced target: **800 ppm** — Remedy: HVAC fresh air "
                "recalibration within authorised +20% energy budget.")

        display_daily = daily.rename(columns={
            'date': 'Date',
            'exceedance_hours': 'Exceedance Hours',
            'peak_co2': 'Peak CO₂ (ppm)',
            'events': 'Events',
        })
        st.dataframe(display_daily, width='stretch', hide_index=True, height=380)
    else:
        st.success("No S08 high-demand IEQ gaps detected.")

    st.divider()

    # ── Event table with drill-down ────────────────────────────────────────────
    st.markdown("#### IEQ Event Log")
    st.caption("All indoor environment quality events. Click column headers to sort.")

    ieq_events = fact[fact['scenario'].isin(['S06', 'S08'])].copy()
    ieq_events = ieq_events.sort_values('event_time')

    ieq_events['Audit Check'] = ieq_events['scenario'].map(display_scenario)
    ieq_display = ieq_events[[
        'event_id', 'asset_id', 'Audit Check', 'event_time',
        'peak_co2_ppm', 'anomaly_duration_mins', 'detail'
    ]].rename(columns={
        'event_id': 'Event ID',
        'asset_id': 'Site',
        'event_time': 'Time',
        'peak_co2_ppm': 'Peak CO₂',
        'anomaly_duration_mins': 'Duration (mins)',
        'detail': 'Recommendation',
    })
    ieq_display['Site'] = ieq_display['Site'].apply(display_asset)

    st.dataframe(ieq_display, width='stretch', hide_index=True)

with tab3:
    st.subheader("Energy Performance — Facilities & Energy Compliance View")
    st.caption("Three views: NABERSNZ benchmark position for every monitored "
               "asset, the energy event timeline for November, and the "
               "underlying event log with full financial quantification.")

    # ── NABERSNZ benchmark chart ───────────────────────────────────────────────
    st.markdown("#### NABERSNZ Benchmark — YTD Energy Intensity by Asset")

    try:
        nab = pd.read_csv(DATA_PATH / "nabersnz_summary.csv")
        nab['Asset'] = nab['asset_id'].apply(display_asset)
        nab['Status'] = nab['breach'].map({True: 'Above Budget', False: 'Within Budget'})

        budget_line = nab['budget_mj_sqm'].iloc[0]

        bars = alt.Chart(nab).mark_bar(size=14).encode(
            y=alt.Y('Asset:N', title=None,
                    sort=alt.EncodingSortField(field='ytd_actual_mj_sqm', order='ascending'),
                    axis=alt.Axis(labelLimit=250)),
            x=alt.X('ytd_actual_mj_sqm:Q', title='YTD Energy Intensity (MJ/sqm)'),
            color=alt.Color('Status:N',
                scale=alt.Scale(domain=['Within Budget', 'Above Budget'],
                                range=['#2ECC71', '#E74C3C']),
                legend=alt.Legend(title=None, orient='top')),
            tooltip=['Asset',
                     alt.Tooltip('ytd_actual_mj_sqm:Q', title='Actual MJ/sqm'),
                     alt.Tooltip('nabersnz_ratio:Q', title='Ratio', format='.3f')],
        )
        rule = alt.Chart(pd.DataFrame({'x': [budget_line]})).mark_rule(
            color='#4A5568', strokeDash=[6, 4], size=2
        ).encode(x='x:Q')

        # Asset_09 HIGH_DEMAND: authorised +20% budget tick
        a09_name = display_asset('Asset_09_NZ_Boundary')
        a09_budget = budget_line * 1.2
        a09_tick = alt.Chart(pd.DataFrame({
            'Asset': [a09_name], 'x': [a09_budget]
        })).mark_tick(
            color='#6C3483', thickness=3, size=22, orient='vertical'
        ).encode(
            y=alt.Y('Asset:N', sort=None),
            x='x:Q',
            tooltip=[alt.Tooltip('x:Q', title='Authorised budget', format='.1f')],
        )

        st.markdown("**New Zealand — NABERSNZ 5-Star Benchmark**")
        st.caption("Red = above budget threshold (ratio > 1.10). "
                   "Asset_03 excluded — data completeness below 95%.")
        st.altair_chart((bars + rule + a09_tick).properties(height=320),
                        use_container_width=True)
        st.caption(f"Dashed line: NABERSNZ climate-adjusted budget = "
                   f"{budget_line:.1f} MJ/sqm (42.0 base + 0.08 × CDD, "
                   f"AS/NZS 3598.1:2014). Purple tick beside {a09_name}: "
                   f"authorised +20% energy budget ({a09_budget:.1f} MJ/sqm) "
                   f"for the high-demand zone to support enhanced IEQ standards.")

        st.markdown("---")

        # ── AU benchmark chart (NABERS Energy) ────────────────────────────────
        st.markdown("---")

        # ── AU benchmark chart (NABERS Energy) ────────────────────────────────
        st.markdown("**Australia — NABERS Energy 5-Star Benchmark**")

        au_csv = DATA_PATH / "nabers_au_summary.csv"
        if not au_csv.exists():
            st.warning("AU energy benchmark unavailable — run compliance_audit.py first.")
        else:
            au_nab = pd.read_csv(au_csv)
            au_row = au_nab.iloc[0]
            au_suspended = bool(au_row.get('suspended', True))
            au_budget    = float(au_row['budget_mj_sqm'])
            au_mj_sqm    = float(au_row['ytd_actual_mj_sqm'])
            au_asset_name = display_asset(au_row['asset_id'])

            if au_suspended:
                st.caption("Energy consumption data is under review pending invoice "
                           "integrity confirmation. Intensity shown is a first-order "
                           "proxy (NABERS base building methodology). "
                           "Verified billing data required for production use.")
                au_status = 'Under Review'
                bar_color  = '#A0ADB8'
                bar_opacity = 0.45
            else:
                st.caption("Energy intensity calculated from verified invoice data. "
                           "Benchmarked against NABERS Energy 5-star reference for "
                           "Sydney CBD office.")
                au_status = 'Above Budget' if bool(au_row['breach']) else 'Within Budget'
                bar_color  = '#E74C3C' if au_status == 'Above Budget' else '#2ECC71'
                bar_opacity = 1.0

            au_df = pd.DataFrame({
                'Asset':       [au_asset_name],
                'ytd_mj_sqm':  [au_mj_sqm],
                'Status':      [au_status],
            })

            au_bars = alt.Chart(au_df).mark_bar(size=14, opacity=bar_opacity).encode(
                y=alt.Y('Asset:N', title=None, axis=alt.Axis(labelLimit=250)),
                x=alt.X('ytd_mj_sqm:Q', title='YTD Energy Intensity (MJ/sqm)'),
                color=alt.Color('Status:N',
                    scale=alt.Scale(
                        domain=[au_status],
                        range=[bar_color]),
                    legend=alt.Legend(title=None, orient='top')),
                tooltip=[alt.Tooltip('ytd_mj_sqm:Q',
                                     title='MJ/sqm (unverified)' if au_suspended else 'MJ/sqm',
                                     format='.1f')],
            )

            au_rule = alt.Chart(pd.DataFrame({'x': [au_budget]})).mark_rule(
                color='#4A5568', strokeDash=[6, 4], size=2
            ).encode(x='x:Q')

            au_label = alt.Chart(pd.DataFrame({
                'x': [au_budget + 2],
                'y': [au_asset_name],
                'text': ['5-star benchmark'],
            })).mark_text(
                align='left', fontSize=11, color='#4A5568', fontStyle='italic'
            ).encode(x='x:Q', y=alt.Y('y:N'), text='text:N')

            au_annotation = alt.Chart(pd.DataFrame({
                'x': [au_mj_sqm - 2],
                'y': [au_asset_name],
                'text': ['⚠ Data under review' if au_suspended else ''],
            })).mark_text(
                align='right', fontSize=11, color='#7D6608', fontWeight='bold'
            ).encode(x='x:Q', y=alt.Y('y:N'), text='text:N')

            st.altair_chart(
                (au_bars + au_rule + au_label + au_annotation).properties(height=120),
                use_container_width=True)
            st.caption(
                f"Dashed line: NABERS Energy 5-star benchmark = {au_budget:.0f} MJ/sqm "
                f"(Sydney CBD office, indicative — NABERS 2023 Technical Guidelines, "
                f"Clean Energy Regulator). "
                f"{'Estimated' if au_suspended else 'Verified'} intensity = {au_mj_sqm:.1f} MJ/sqm "
                f"(floor area {int(au_row['area_sqm']):,} sqm). "
                f"Building Energy Efficiency Disclosure Act 2010 (Cth) applies.")
    except FileNotFoundError:
        st.warning("nabersnz_summary.csv not found — run energy_audit.py first.")

    st.divider()

    # ── Energy event timeline ──────────────────────────────────────────────────
    st.markdown("#### Energy Event Timeline — November 2025")
    st.caption("Each row is a site; each marker is a detected event. "
               )

    energy_events = fact[fact['scenario'].isin(['S04', 'S05', 'S07'])].copy()

    if not energy_events.empty:
        energy_events['end_time'] = (
            energy_events['event_time'] +
            pd.to_timedelta(energy_events['anomaly_duration_mins'], unit='m')
        )
        energy_events['Asset'] = energy_events['asset_id'].apply(display_asset)
        LABELS = {'S04': 'Sub-Meter Drift', 'S05': 'After-Hours Waste',
                  'S07': 'Efficiency Degradation'}
        energy_events['Scenario'] = energy_events['scenario'].map(LABELS)

        asset_order = sorted(energy_events['Asset'].unique())

        # Short events (S04/S05): point markers so none disappear
        short_ev = energy_events[energy_events['scenario'].isin(['S04', 'S05'])]
        # Long-period events (S07): translucent span showing coverage period
        long_ev  = energy_events[energy_events['scenario'] == 'S07']

        base_tooltip = ['Asset', 'Scenario',
                        alt.Tooltip('event_time:T', title='Start'),
                        alt.Tooltip('anomaly_duration_mins:Q', title='Duration (mins)'),
                        alt.Tooltip('waste_kwh:Q', title='Waste kWh', format='.1f'),
                        alt.Tooltip('financial_cost:Q', title='Cost NZD', format='.2f')]

        span = alt.Chart(long_ev).mark_bar(height=16).encode(
            x=alt.X('event_time:T', title='Date (November 2025)',
                    axis=alt.Axis(format='%d', tickCount='day', labelAngle=0),
                    scale=alt.Scale(domain=['2025-11-01', '2025-11-30T23:59:59'])),
            x2='end_time:T',
            y=alt.Y('Asset:N', title=None, sort=asset_order,
                    scale=alt.Scale(domain=asset_order),
                    axis=alt.Axis(labelLimit=250)),
            color=alt.Color('Scenario:N',
                scale=alt.Scale(domain=['Sub-Meter Drift', 'After-Hours Waste', 'Efficiency Degradation'],
                                range=['#1F5FA8', '#E67E22', 'rgba(192,57,43,0.35)']),
                legend=alt.Legend(title=None, orient='top')),
            tooltip=base_tooltip,
        )

        points = alt.Chart(short_ev).mark_point(
            size=110, filled=True, shape='square'
        ).encode(
            x=alt.X('event_time:T', title='Date (November 2025)',
                    axis=alt.Axis(format='%d', tickCount='day', labelAngle=0),
                    scale=alt.Scale(domain=['2025-11-01', '2025-11-30T23:59:59'])),
            y=alt.Y('Asset:N', title=None, sort=asset_order,
                    scale=alt.Scale(domain=asset_order),
                    axis=alt.Axis(labelLimit=250)),
            color=alt.Color('Scenario:N',
                scale=alt.Scale(domain=['Sub-Meter Drift', 'After-Hours Waste', 'Efficiency Degradation'],
                                range=['#1F5FA8', '#E67E22', '#C0392B']),
                legend=None),
            tooltip=base_tooltip,
        )
        st.altair_chart((span + points).properties(height=300),
                        use_container_width=True)
        st.caption("Square markers: individual short events (sub-meter drift, "
                   "after-hours waste). Translucent band: efficiency degradation "
                   "coverage period — the span over which cumulative "
                   "drift was detected, not continuous alarms.")
    else:
        st.success("No energy events detected.")

    st.divider()

    # ── Event log ──────────────────────────────────────────────────────────────
    st.markdown("#### Energy Event Log")
    st.caption("All energy events with financial quantification. "
               "Click column headers to sort.")

    elog = fact[fact['scenario'].isin(['S04', 'S05', 'S07', 'S10'])].copy()
    elog = elog.sort_values('event_time')
    elog['Audit Check'] = elog['scenario'].map(display_scenario)
    elog_display = elog[[
        'event_id', 'asset_id', 'Audit Check', 'event_time',
        'anomaly_duration_mins', 'waste_kwh', 'financial_cost', 'carbon_kg'
    ]].rename(columns={
        'event_id': 'Event ID',
        'asset_id': 'Site',
        'event_time': 'Time',
        'anomaly_duration_mins': 'Duration (mins)',
        'waste_kwh': 'Waste kWh',
        'financial_cost': 'Cost (NZD)',
        'carbon_kg': 'Carbon (kgCO₂e)',
    })
    elog_display['Site'] = elog_display['Site'].apply(display_asset)
    st.dataframe(elog_display, width='stretch', hide_index=True)

with tab4:
    st.subheader("Evidence & Scope 3 — Finance & ESG Compliance View")
    st.caption("Document integrity verification, billing reconciliation status, "
               "and Scope 3 compliance findings. Only records requiring "
               "attention are shown.")

    # ── Document integrity (S02) ───────────────────────────────────────────────
    st.markdown("#### Document Integrity — Flagged Invoices")
    st.caption("Utility invoices whose cryptographic hash failed verification. "
               "A failed check means the submitted document does not match the "
               "original signed at source — the invoice cannot be used as "
               "audit evidence until re-submitted.")

    s02 = fact[fact['scenario'] == 'S02'].copy()
    if not s02.empty:
        s02_display = s02[['asset_id', 'detail']].rename(columns={
            'asset_id': 'Site',
            'detail': 'Finding',
        })
        s02_display['Site'] = s02_display['Site'].apply(display_asset)
        st.dataframe(s02_display, width='stretch', hide_index=True,
                     column_config={
                         'Finding': st.column_config.TextColumn(width='large'),
                     })
    else:
        st.success("All invoice hashes verified.")

    st.divider()

    # ── Billing reconciliation (S09) ───────────────────────────────────────────
    st.markdown("#### Billing Reconciliation — Sydney Office")
    st.caption("For facilities without IoT metering, billed consumption is "
               "compared against the NABERS office benchmark "
               "(265 MJ/sqm/year, FY2020 median).")

    s09 = fact[fact['scenario'] == 'S09'].copy()
    if not s09.empty:
        for _, row in s09.iterrows():
            if 'SUSPENDED' in str(row['status']):
                st.warning(f"**{display_asset(row['asset_id'])}** — Invoice "
                           f"authenticity under review. Billing variance "
                           f"analysis will resume once document integrity "
                           f"is confirmed.")
            else:
                st.error(f"**{display_asset(row['asset_id'])}** — "
                         f"{row['detail']} | Exposure: "
                         f"AUD {row['financial_exposure']:,.2f}")
    else:
        st.success("Billing within expected range.")

    st.divider()

    # ── Scope 3: Travel (S11) ──────────────────────────────────────────────────
# ── Scope 3: Travel (S11) ──────────────────────────────────────────────────
    st.markdown("#### Scope 3 — Business Travel Class Audit")
    st.caption("Business class bookings on routes under 6 hours, identified "
               "from e-ticket fare basis codes. Cabin class materially "
               "affects per-passenger emissions (GHG Protocol Category 6).")

    s11 = fact[fact['scenario'] == 'S11'].copy()
    if not s11.empty:
        s11['ticket_price_display'] = s11['financial_exposure'].apply(
            lambda x: f"AUD {x:,.0f}")
        s11_display = s11[['asset_id', 'ticket_price_display',
                           'detail']].rename(columns={
            'asset_id': 'Employee',
            'ticket_price_display': 'Ticket Price',
            'detail': 'Finding',
        })
        st.dataframe(s11_display, width='stretch', hide_index=True,
                     column_config={
                         'Finding': st.column_config.TextColumn(width='large'),
                     })
    else:
        st.success("No travel class findings.")

    st.divider()

    # ── Scope 3: Waste (S12) ───────────────────────────────────────────────────
    st.markdown("#### Scope 3 — Hazardous Waste Disposal")
    st.caption("Hazardous and E-Waste manifests must carry a disposal "
               "certificate from a licensed handler (HSNO Act 1996, "
               "Basel Convention, GRI 306:2020).")

    s12 = fact[fact['scenario'] == 'S12'].copy()
    if not s12.empty:
        s12_display = s12[['asset_id', 'detail']].rename(columns={
            'asset_id': 'Site',
            'detail': 'Finding',
        })
        s12_display['Site'] = s12_display['Site'].apply(display_asset)
        st.dataframe(s12_display, width='stretch', hide_index=True,
                     column_config={
                         'Finding': st.column_config.TextColumn(width='large'),
                     })
    else:
        st.success("All hazardous waste disposals certified.")

    st.divider()

    # ── Full evidence log ──────────────────────────────────────────────────────
    st.markdown("#### Evidence & Scope 3 Event Log")
    st.caption("All compliance events with reference IDs for audit traceability.")

    comp_events = fact[fact['category'] == 'Compliance'].copy()
    comp_events['Audit Check'] = comp_events['scenario'].map(display_scenario)
    comp_events['Standard Breached'] = comp_events['scenario'].map(SCEN_STD)

    for _, ev in comp_events.iterrows():
        site = (display_asset(ev['asset_id'])
                if 'Asset' in str(ev['asset_id']) else ev['asset_id'])
        detail_text = str(ev['detail']).replace(
            'S09 analysis suspended — upstream S02 hash breach unresolved.',
            'Analysis suspended — invoice authenticity under review.')

        with st.expander(f"{ev['event_id']}  ·  {site}  ·  {ev['Audit Check']}"):
            st.markdown(f"**Standard Breached:** {ev['Standard Breached']}")
            st.markdown(f"**Finding:** {detail_text}")
