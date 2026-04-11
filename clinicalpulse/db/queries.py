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

LAB_TIMESERIES = """
WITH cohort AS (
    SELECT unnest(CAST(:hadm_ids AS int[])) AS hadm_id
),
item AS (
    SELECT itemid FROM mimiciv_hosp.d_labitems
    WHERE LOWER(label) = LOWER(:lab_name)
    LIMIT 1
),
daily AS (
    SELECT
        DATE_TRUNC('day', l.charttime)          AS day,
        PERCENTILE_CONT(0.5) WITHIN GROUP
            (ORDER BY l.valuenum)               AS median_value,
        COUNT(*)                                AS sample_count,
        MIN(l.valuenum)                         AS min_value,
        MAX(l.valuenum)                         AS max_value,
        l.valueuom                              AS unit
    FROM mimiciv_hosp.labevents l
    JOIN cohort c ON c.hadm_id = l.hadm_id
    JOIN item i ON i.itemid = l.itemid
    WHERE l.valuenum IS NOT NULL
    GROUP BY DATE_TRUNC('day', l.charttime), l.valueuom
),
recent AS (
    SELECT * FROM daily
    ORDER BY day DESC
    LIMIT :days
)
SELECT * FROM recent ORDER BY day ASC;
"""

LAB_LOOKUP = """
SELECT itemid, label, ref_range_lower, ref_range_upper
FROM mimiciv_hosp.d_labitems
LEFT JOIN LATERAL (
    SELECT ref_range_lower, ref_range_upper
    FROM mimiciv_hosp.labevents
    WHERE itemid = d_labitems.itemid
      AND ref_range_lower IS NOT NULL
    LIMIT 1
) r ON true
WHERE LOWER(label) = LOWER(:lab_name)
LIMIT 1;
"""

PATIENT_TIMELINE = """
SELECT
    a.hadm_id,
    a.admittime,
    a.dischtime,
    a.admission_type,
    a.discharge_location,
    a.hospital_expire_flag,
    EXTRACT(EPOCH FROM (a.dischtime - a.admittime)) / 3600.0 AS los_hours,
    json_agg(
        json_build_object(
            'seq_num',   d.seq_num,
            'icd_code',  d.icd_code,
            'long_title', di.long_title
        ) ORDER BY d.seq_num
    ) AS diagnoses
FROM mimiciv_hosp.admissions a
LEFT JOIN mimiciv_hosp.diagnoses_icd d ON d.hadm_id = a.hadm_id
LEFT JOIN mimiciv_hosp.d_icd_diagnoses di
    ON di.icd_code = d.icd_code AND di.icd_version = d.icd_version
WHERE a.subject_id = :subject_id
GROUP BY a.hadm_id, a.admittime, a.dischtime,
         a.admission_type, a.discharge_location, a.hospital_expire_flag
ORDER BY a.admittime;
"""
