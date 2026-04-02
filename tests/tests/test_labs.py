async def test_lab_timeseries(client):
    define = await client.post("/cohort/define", json={"age_min": 50, "age_max": 80})
    cohort_id = define.json()["cohort_id"]

    resp = await client.get(f"/cohort/{cohort_id}/labs/Creatinine")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cohort_id"] == cohort_id
    assert data["lab_name"] == "Creatinine"
    assert len(data["timeseries"]) > 0


async def test_lab_timeseries_with_days(client):
    define = await client.post("/cohort/define", json={"age_min": 50, "age_max": 80})
    cohort_id = define.json()["cohort_id"]

    resp = await client.get(f"/cohort/{cohort_id}/labs/Creatinine?days=5")
    assert resp.status_code == 200
    assert len(resp.json()["timeseries"]) <= 5


async def test_lab_not_found(client):
    define = await client.post("/cohort/define", json={"age_min": 50, "age_max": 80})
    cohort_id = define.json()["cohort_id"]

    resp = await client.get(f"/cohort/{cohort_id}/labs/FakeLab")
    assert resp.status_code == 404
    assert resp.json()["error"] == "LabNotFound"
