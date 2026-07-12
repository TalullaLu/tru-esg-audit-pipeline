# TRU-ESG Audit Pipeline

**An automated assurance layer for multi-jurisdictional ESG disclosure — New Zealand & Australia**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/Data-PostgreSQL%20%2F%20CSV-336791?logo=postgresql&logoColor=white)
![Standards](https://img.shields.io/badge/Aligned-NABERS%20%7C%20WELL%20%7C%20GHG%20Protocol%20%7C%20IPMVP-2E8B57)
![Status](https://img.shields.io/badge/Status-Audit--Ready%20MVP-success)

🔗 **Live dashboard:** [tru-esg-audit-pipeline.streamlit.app](https://tru-esg-audit-pipeline.streamlit.app/)

---

## The Problem

ESG assurance is moving from voluntary reporting to regulated, audit-grade disclosure — yet the underlying data was never built to withstand that scrutiny. A number that cannot be traced to its source is, in assurance terms, unverified. And unverified disclosure is no longer merely a reputational risk; it is a legal and regulatory one.

**TRU-ESG is built for this gap.** It is an assurance layer, not a carbon calculator — sitting between raw IoT telemetry and boardroom disclosure, aligning source data to the standards that govern ESG reporting (NABERSNZ, NABERS, WELL, GHG Protocol, IPMVP) and surfacing the integrity failures and compliance gaps that conventional frameworks assume away.

---

## Why It Matters

- **Efficiency & traceability** — every asset and interval audited automatically; every figure traces back to a specific event, timestamp, and regulatory clause.
- **Prioritised decisions** — findings ranked by financial, regulatory, and reputational exposure; unverified evidence is withheld from disclosure rather than reported as a false number.
- **Recoverable value** — quantifies avoidable carbon and cost, plus the staff productivity protected by maintaining air quality in premium zones (per Allen et al., 2019, Harvard).

---

## How It Works

**Inputs** → sensor telemetry (IoT CO₂, temperature, HVAC, sub-meters); financial evidence (invoices, travel records); compliance documents (waste certificates); reference data (asset registry, climate benchmarks).

**Processing** → twelve scenarios evaluate the data across three problem classes — integrity, operational anomaly, compliance gap — each anchored to a named standard. Cascade logic suspends downstream analysis when upstream evidence cannot be trusted.

**Outputs** → a machine-readable star schema for BI and audit teams, and a four-page Streamlit dashboard (Executive · IEQ · Energy · Evidence & Scope 3).

---

## Dashboard
### Executive Dashboard
![Executive Dashboard](screenshots/Dashboard.jpg)

### IEQ Intelligence - Indoor Air Quality
![IEQ Indoor Air Quality](screenshots/Dashboard%202.jpg)

### Energy Performance - Greenbuilding Benchmark
![Green Building Benchmark](screenshots/Dashboard%203.jpg)

---
## Audit Coverage
Twelve scenarios across five domains, each anchored to a named standard:

- **Data Integrity & Assurance** — device authorisation, invoice integrity, telemetry completeness
- **Energy Performance & Scope 2** — sub-metering, after-hours waste, efficiency degradation, NABERSNZ compliance
- **Indoor Environment Quality** — ventilation compliance, high-demand zone air quality
- **Scope 3 & Value Chain** — billing variance, business travel emissions
- **Waste & Circularity** — hazardous waste certification

Full scenario detail, regulatory mapping, and detection logic: see [Scenario Library](docs/).

> **Note on IP:** This repository demonstrates the pipeline's architecture, standards alignment, and detection logic. Specific thresholds, coefficients, and scoring formulas have been generalised; full methodology is available for discussion in a technical or interview setting.

---

## Tech Stack

Python (Pandas, NumPy) · SQLAlchemy · PostgreSQL (Google Cloud SQL) with local CSV fallback · Streamlit · Altair · star-schema data model.

Frameworks: ISAE 3000 · GHG Protocol · IPMVP · NABERS / NABERSNZ · WELL v2.

---

## Getting Started

```bash
git clone https://github.com/TalullaLu/tru-esg-audit-pipeline.git
cd tru-esg-audit-pipeline
pip install -r requirements.txt

# Run the audit engines, then launch the dashboard
python facility_audit.py && python energy_audit.py && python compliance_audit.py && python Final_Table.py
streamlit run app.py
```

The repository ships with complete **synthetic data** (no real client information), so the full pipeline runs out of the box. Cloud database connection is optional, via a local `.env` file (not included).

---

## About

Built by **Talulla Lu** — Master of Business Analytics (University of Waikato, 2026), with 7 years of APAC experience across green building and environmental monitoring. TRU-ESG reflects a simple conviction: ESG is an **evidence problem, not a reporting problem**. The organisations that win the trust of investors and regulators will be those who can *prove* their numbers — not just publish them.

📧 talulla777@gmail.com

*Synthetic data throughout. Asset names, locations, and figures are illustrative.*
