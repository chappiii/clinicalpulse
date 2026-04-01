COHORT_DEFINE = """
SELECT DISTINCT a.hadm_id, a.subject_id
FROM mimiciv_hosp.admissions a
JOIN mimiciv_hosp.patients p ON p.subject_id = a.subject_id
LEFT JOIN mimiciv_hosp.diagnoses_icd d ON d.hadm_id = a.hadm_id
WHERE 1=1
  AND (CAST(:age_min AS int) IS NULL OR p.anchor_age >= :age_min)
  AND (CAST(:age_max AS int) IS NULL OR p.anchor_age <= :age_max)
  AND (CAST(:gender AS text) IS NULL OR p.gender = :gender)
  AND (CAST(:admission_type AS text) IS NULL OR a.admission_type = :admission_type)
  AND (
    CAST(:icd_codes AS text[]) IS NULL
    OR (d.icd_code = ANY(CAST(:icd_codes AS text[])) AND d.icd_version = :icd_version)
  )
"""

COHORT_METRICS = """
WITH cohort AS (
    SELECT unnest(CAST(:hadm_ids AS int[])) AS hadm_id
),
admissions AS (
    SELECT
        a.hadm_id,
        a.subject_id,
        EXTRACT(EPOCH FROM (a.dischtime - a.admittime)) / 3600.0 AS los_hours,
        a.hospital_expire_flag,
        a.discharge_location
    FROM mimiciv_hosp.admissions a
    JOIN cohort c ON c.hadm_id = a.hadm_id
),
readmissions AS (
    SELECT COUNT(DISTINCT r.hadm_id) AS readmit_count
    FROM mimiciv_hosp.mv_readmissions r
    JOIN cohort c ON c.hadm_id = r.hadm_id
),
top_dx AS (
    SELECT d.icd_code, di.long_title, COUNT(*) AS freq
    FROM mimiciv_hosp.diagnoses_icd d
    JOIN cohort c ON c.hadm_id = d.hadm_id
    JOIN mimiciv_hosp.d_icd_diagnoses di
        ON di.icd_code = d.icd_code AND di.icd_version = d.icd_version
    WHERE d.seq_num = 1
    GROUP BY d.icd_code, di.long_title
    ORDER BY freq DESC
    LIMIT 5
)
SELECT
    COUNT(*)                                                    AS total_admissions,
    ROUND(CAST(AVG(los_hours) AS numeric), 1)                   AS avg_los_hours,
    ROUND(CAST(AVG(hospital_expire_flag) AS numeric) * 100, 1)  AS mortality_rate_pct,
    (SELECT readmit_count FROM readmissions)                    AS readmit_count,
    (SELECT json_agg(row_to_json(top_dx)) FROM top_dx)         AS top_diagnoses
FROM admissions;
"""
