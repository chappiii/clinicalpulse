async def test_patient_timeline(client):
    resp = await client.get("/patient/10000032/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["subject_id"] == 10000032
    assert len(data["admissions"]) > 0
    admission = data["admissions"][0]
    assert "hadm_id" in admission
    assert "diagnoses" in admission


async def test_patient_not_found(client):
    resp = await client.get("/patient/99999999/timeline")
    assert resp.status_code == 404
    assert resp.json()["error"] == "PatientNotFound"
