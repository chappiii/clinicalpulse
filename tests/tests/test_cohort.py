async def test_define_cohort(client):
    resp = await client.post("/cohort/define", json={"age_min": 50, "age_max": 80})
    assert resp.status_code == 200
    data = resp.json()
    assert "cohort_id" in data
    assert data["patient_count"] > 0
    assert data["admission_count"] > 0
    assert data["filters_applied"] == {"age_min": 50, "age_max": 80}


async def test_define_cohort_empty_filters(client):
    resp = await client.post("/cohort/define", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["admission_count"] > 0


async def test_cohort_metrics(client):
    define = await client.post("/cohort/define", json={"age_min": 50, "age_max": 80})
    cohort_id = define.json()["cohort_id"]

    resp = await client.get(f"/cohort/{cohort_id}/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cohort_id"] == cohort_id
    assert data["total_admissions"] > 0
    assert "avg_los_hours" in data
    assert "mortality_rate_pct" in data
    assert "top_diagnoses" in data


async def test_cohort_metrics_not_found(client):
    resp = await client.get("/cohort/00000000-0000-0000-0000-000000000000/metrics")
    assert resp.status_code == 404
    assert resp.json()["error"] == "CohortNotFound"
