# Hospital Readmission Risk Analysis
Clinical data analysis of 30-day hospital readmission patterns using the MIMIC-III dataset.

## Dashboard Preview
![Hospital Readmission Risk Analysis Dashboard](dashboard-screenshot.png)

## Key Findings
- **6.37% overall 30-day readmission rate** — 3,384 readmissions out of 53,122 eligible admissions
- **Medicare patients are disproportionately readmitted**: 57.74% of all readmissions, vs. 45.76% of eligible admissions overall
- **HOME HEALTH CARE and HOME discharges account for 47.49% of readmissions**, pointing to gaps in post-discharge support
- **Highest-risk combination**: Acute Respiratory Failure + Medicare + SNF discharge — 30 cases, averaging 11.0 days to readmission

## Clinical Recommendation
Implement pharmacist-led medication reconciliation calls at day 7 post-discharge for Medicare patients discharged home with cardiac or respiratory diagnoses. This targets the population and time window where risk is concentrated: Medicare patients discharged to home/home health care are readmitted most often, and the average time-to-readmission across the highest-risk diagnosis groups is roughly 11 days — a day-7 call falls before that window closes, while medication issues are still correctable.

## Background
Unplanned 30-day readmissions cost the US healthcare system over $26 billion annually. Hospitals face direct financial penalties from CMS for high readmission rates. This analysis approaches the problem from both a clinical and data perspective — combining pharmacy knowledge with health informatics methodology.

## Tools Used
- SQL — data extraction and analysis
- Excel — data cleaning and exploration
- Tableau Public — interactive dashboard and visualization
- GitHub — version control and portfolio

## Dataset
MIMIC-III Clinical Database — [PhysioNet](https://physionet.org/content/mimiciii/). Access requires CITI certification and credentialing approval.

## Project Status
🟢 Analysis Complete

## Author
Ridham Patel · Masters in Health Informatics · University of Scranton

## Progress Log
- **April 27, 2026** — Project initiated. CITI certified. PhysioNet application submitted. GitHub repository created. SQL environment set up. Core query logic developed and tested.
- **April 28, 2026** — SQL practice completed. Core concepts mastered: SELECT, WHERE, GROUP BY, JOIN, HAVING, ORDER BY. Multi-table clinical readmission analysis queries written and tested.
- **May 21, 2026** — MIMIC-III access granted. Four tables imported. First queries executed using a self-join approach.
- **July 15, 2026** — Identified that the self-join methodology double-counted readmissions for patients with 3+ admissions. Rebuilt the analysis using LEAD() window functions to pair each admission with only its next chronological admission. Corrected rate: 6.37% (3,384 readmissions / 53,122 eligible admissions). Updated all breakdown CSVs, SQL, and dashboard to reflect the corrected methodology.
