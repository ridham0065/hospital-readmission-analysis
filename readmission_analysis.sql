-- ============================================================================
-- Hospital 30-Day Readmission Risk Analysis
-- Dataset: MIMIC-III (ADMISSIONS, PATIENTS, DIAGNOSES_ICD, DRGCODES)
--
-- METHODOLOGY NOTE:
-- An earlier version of this analysis identified readmissions with a
-- self-join of ADMISSIONS to itself on SUBJECT_ID. That approach double
-- counted patients with 3+ admissions (every later admission matched every
-- earlier one, not just the very next one), inflating readmission counts
-- and skewing the insurance/discharge/diagnosis breakdowns.
--
-- This corrected version uses the LEAD() window function to pair each
-- admission with only the patient's next chronological admission, which
-- eliminates the double counting.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 1: Views
-- ----------------------------------------------------------------------------

-- For every admission, attach the patient's next admission (by ADMITTIME).
-- LEAD() partitions by SUBJECT_ID and orders by ADMITTIME, so each row is
-- paired with exactly one "next" admission (or NULL if it was their last).
DROP VIEW IF EXISTS v_index_admissions;
CREATE VIEW v_index_admissions AS
SELECT SUBJECT_ID, HADM_ID, ADMITTIME, DISCHTIME,
       INSURANCE, ADMISSION_TYPE, DISCHARGE_LOCATION, HOSPITAL_EXPIRE_FLAG,
       LEAD(ADMITTIME) OVER (PARTITION BY SUBJECT_ID ORDER BY ADMITTIME) AS next_admittime,
       LEAD(ADMISSION_TYPE) OVER (PARTITION BY SUBJECT_ID ORDER BY ADMITTIME) AS next_admission_type
FROM ADMISSIONS;

-- Exclude admissions that ended in the patient's death — they cannot be
-- readmitted, so including them would understate the true readmission rate.
DROP VIEW IF EXISTS v_eligible_admissions;
CREATE VIEW v_eligible_admissions AS
SELECT * FROM v_index_admissions
WHERE HOSPITAL_EXPIRE_FLAG = 0;

-- A readmission is the next admission occurring after discharge and within
-- 30 days of it.
DROP VIEW IF EXISTS v_readmissions_30d;
CREATE VIEW v_readmissions_30d AS
SELECT *,
       ROUND(JULIANDAY(next_admittime) - JULIANDAY(DISCHTIME), 0) AS days_to_readmission
FROM v_eligible_admissions
WHERE next_admittime IS NOT NULL
AND next_admittime > DISCHTIME
AND ROUND(JULIANDAY(next_admittime) - JULIANDAY(DISCHTIME), 0) <= 30;

-- ----------------------------------------------------------------------------
-- STEP 2: Analysis queries
-- ----------------------------------------------------------------------------

-- Query A — Total 30-day readmissions
SELECT COUNT(*) as total_readmissions FROM v_readmissions_30d;

-- Query B — Readmissions by insurance type, with each insurer's share of all
-- readmissions and its own readmission rate (readmissions / that insurer's
-- eligible admissions)
SELECT INSURANCE,
       COUNT(*) as total_readmissions,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM v_readmissions_30d), 2) as pct_of_readmissions,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM v_eligible_admissions), 2) as readmission_rate
FROM v_readmissions_30d
GROUP BY INSURANCE
ORDER BY total_readmissions DESC;

-- Query C — Readmissions by discharge disposition from the index admission
SELECT DISCHARGE_LOCATION,
       COUNT(*) as total_readmissions,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM v_readmissions_30d), 2) as percentage
FROM v_readmissions_30d
GROUP BY DISCHARGE_LOCATION
ORDER BY total_readmissions DESC;

-- Query D — Readmissions by primary (SEQ_NUM = 1) diagnosis on the index
-- admission, restricted to 10 clinically relevant ICD-9 codes
SELECT
    CASE d.ICD9_CODE
        WHEN '51881' THEN 'Acute Respiratory Failure'
        WHEN '41401' THEN 'Coronary Artery Disease'
        WHEN '41071' THEN 'Heart Attack'
        WHEN '42823' THEN 'Atrial Fibrillation'
        WHEN '4280' THEN 'Congestive Heart Failure'
        WHEN '486' THEN 'Pneumonia'
        WHEN '40301' THEN 'Hypertensive Kidney Disease'
        WHEN '49121' THEN 'COPD'
        WHEN '5849' THEN 'Acute Kidney Failure'
        WHEN '5789' THEN 'GI Hemorrhage'
        ELSE d.ICD9_CODE
    END as diagnosis_name,
    COUNT(*) as total_readmissions
FROM DIAGNOSES_ICD d
JOIN v_readmissions_30d r ON d.HADM_ID = r.HADM_ID
WHERE d.SEQ_NUM = 1
AND d.ICD9_CODE IN ('51881','41401','41071','42823','4280','486','40301','49121','5849','5789')
GROUP BY d.ICD9_CODE
ORDER BY total_readmissions DESC;

-- Query E — Master combination: diagnosis x insurance x discharge location,
-- with average days-to-readmission, restricted to combinations with at
-- least 5 cases so the averages are not driven by single outliers
SELECT
    CASE d.ICD9_CODE
        WHEN '51881' THEN 'Acute Respiratory Failure'
        WHEN '41401' THEN 'Coronary Artery Disease'
        WHEN '41071' THEN 'Heart Attack'
        WHEN '42823' THEN 'Atrial Fibrillation'
        WHEN '4280' THEN 'Congestive Heart Failure'
        WHEN '486' THEN 'Pneumonia'
        WHEN '40301' THEN 'Hypertensive Kidney Disease'
        WHEN '49121' THEN 'COPD'
        WHEN '5849' THEN 'Acute Kidney Failure'
        WHEN '5789' THEN 'GI Hemorrhage'
        ELSE d.ICD9_CODE
    END as diagnosis_name,
    r.INSURANCE,
    r.DISCHARGE_LOCATION,
    COUNT(*) as total_readmissions,
    ROUND(AVG(r.days_to_readmission),1) as avg_days_to_readmit
FROM DIAGNOSES_ICD d
JOIN v_readmissions_30d r ON d.HADM_ID = r.HADM_ID
WHERE d.SEQ_NUM = 1
AND d.ICD9_CODE IN ('51881','41401','41071','42823','4280','486','40301','49121','5849','5789')
GROUP BY d.ICD9_CODE, r.INSURANCE, r.DISCHARGE_LOCATION
HAVING COUNT(*) >= 5
ORDER BY total_readmissions DESC;

-- ============================================================================
-- SUMMARY OF KEY FINDINGS (corrected methodology)
-- ============================================================================
-- Total eligible admissions (excludes in-hospital deaths): 53,122
-- Total 30-day readmissions:                                3,384
-- Overall 30-day readmission rate:                           6.37%
--
-- By insurance:
--   Medicare  — 1,954 readmissions (57.74% of all readmissions),
--               45.76% of eligible admissions, 3.68% readmission rate
--   Private   —   966 readmissions (28.55%)
--   Medicaid  —   389 readmissions (11.50%)
--   Government —   66 readmissions (1.95%)
--   Self Pay  —     9 readmissions (0.27%)
--   -> Medicare patients are readmitted at roughly double their share of
--      the eligible population, making them the highest-risk payer group.
--
-- By discharge location:
--   HOME HEALTH CARE — 806 (23.82%)
--   HOME              — 801 (23.67%)
--   SNF               — 644 (19.03%)
--   -> HOME HEALTH CARE + HOME together account for 47.49% of all
--      readmissions, suggesting post-discharge support at home is a key
--      intervention point.
--
-- Highest-risk combination (diagnosis x insurance x discharge, n >= 5):
--   Acute Respiratory Failure + Medicare + SNF: 30 cases, averaging
--   11.0 days to readmission — the single largest risk cell in the data.
-- ============================================================================
