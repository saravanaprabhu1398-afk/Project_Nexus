"""Phase 1 exit criteria, end to end (Gate 1 evidence).

* NEXUS receives an engineering question
* it creates and maintains an investigation session
* a mock tool is selected and invoked through the complete agent loop
* every request carries an audit and trace identifier
* failed calls produce controlled errors
"""

from __future__ import annotations

BODY = {
    "intent": "diagnose_job_failure",
    "question": "Why did customer_daily_ingestion fail?",
    "resource_refs": [{"type": "databricks_job", "id": "1234", "workspace": "ws"}],
}


async def test_health_and_readiness(client):
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    ready = (await client.get("/readyz")).json()
    assert ready["status"] == "ready"


async def test_create_returns_202_with_correlation_id(client, auth):
    r = await client.post("/v1/investigations", json=BODY, headers=auth)
    assert r.status_code == 202
    payload = r.json()
    assert payload["status"] == "queued"
    assert payload["correlation_id"]
    assert payload["links"]["evidence"].endswith("/evidence")
    assert r.headers["Location"].endswith(payload["id"])


async def test_investigation_completes_with_cited_evidence(client, auth):
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()
    got = await client.get(f"/v1/investigations/{created['id']}", headers=auth)
    assert got.status_code == 200

    body = got.json()
    assert body["status"] == "complete"
    assert body["question"] == BODY["question"]
    assert len(body["evidence"]) == 3
    assert {e["citation_key"] for e in body["evidence"]} == {"EV-01", "EV-02", "EV-03"}
    assert body["consumed"]["tool_calls"] == 3


async def test_audit_trail_is_reconstructable(client, auth):
    """US-08."""
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()
    audit = (await client.get(f"/v1/investigations/{created['id']}/audit", headers=auth)).json()

    assert len(audit) == 3
    for entry in audit:
        assert entry["action"] == "tool.invoke"
        assert entry["subject_id"] == "eng-1"
        assert entry["decision"] == "permit"
        assert entry["policy_id"].startswith("static-v1/")
        assert entry["purpose"] == "diagnose_job_failure"


async def test_unauthenticated_request_is_rejected(client):
    r = await client.post("/v1/investigations", json=BODY)
    assert r.status_code == 401
    assert r.json()["error_code"] == "AUTH_FAILED"


async def test_another_tenant_cannot_read_the_investigation(client, auth):
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()
    other = {**auth, "X-Nexus-Tenant": "pilot-b"}
    r = await client.get(f"/v1/investigations/{created['id']}", headers=other)
    assert r.status_code == 404
    assert r.json()["error_code"] == "RESOURCE_NOT_FOUND"


async def test_missing_resource_ref_is_a_validation_error(client, auth):
    r = await client.post("/v1/investigations", json={**BODY, "resource_refs": []}, headers=auth)
    assert r.status_code == 422


async def test_kill_switch_refuses_new_investigations(client, auth):
    client.app.state.settings.disabled = True
    try:
        r = await client.post("/v1/investigations", json=BODY, headers=auth)
        assert r.status_code == 503
        assert r.json()["error_code"] == "SERVICE_DISABLED"
    finally:
        client.app.state.settings.disabled = False


async def test_abort_moves_to_terminal_state(client, auth):
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()
    r = await client.post(f"/v1/investigations/{created['id']}/abort", headers=auth)
    assert r.status_code == 202
    body = (await client.get(f"/v1/investigations/{created['id']}", headers=auth)).json()
    assert body["status"] == "aborted"
