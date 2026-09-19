import asyncio

async def test_concurrent_first_scoring_does_not_crash(client, unscored_video_id, auth_header):
    results = await asyncio.gather(
        client.get(f"/api/v1/videos/{unscored_video_id}/risk-score", headers=auth_header),
        client.get(f"/api/v1/videos/{unscored_video_id}/risk-score", headers=auth_header),
    )
    assert all(r.status_code == 200 for r in results)
    assert results[0].json()["overall_score"] == results[1].json()["overall_score"]

def test_baseline_recompute_rejects_invalid_movement_type(client, admin_auth_header):
    resp = client.post("/api/v1/baselines/recompute", json={"movement_type": "not_a_real_movement"}, headers=admin_auth_header)
    assert resp.status_code == 422

def test_baseline_recompute_debounced(client, admin_auth_header):
    first = client.post("/api/v1/baselines/recompute", json={"movement_type": "squatting"}, headers=admin_auth_header)
    second = client.post("/api/v1/baselines/recompute", json={"movement_type": "squatting"}, headers=admin_auth_header)
    assert first.status_code == 200
    assert second.status_code == 429
