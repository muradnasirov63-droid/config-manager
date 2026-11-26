"""Расширенные 16 модульных тестов из ЛР№4."""

def _seed_service_and_env(client, svc_name="svc-a", env_name="dev"):
    s = client.post("/services", json={"name": svc_name, "owner": "team"}).json()
    e = client.post("/environments", json={"name": env_name, "namespace": f"{svc_name}-{env_name}"}).json()
    return s["id"], e["id"]


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200 and "config_services_total" in r.text


def test_json_config_service_v1_and_export(client):
    s_id, e_id = _seed_service_and_env(client, "orders", "stage")
    cfg = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "json",
        "schema_ref": "service-v1", "author": "dev",
        "content": '{"service": {"name": "orders", "replicas": 3}}'
    })
    assert cfg.status_code == 201
    exp = client.get(f"/configs/{cfg.json()['id']}/export")
    assert exp.status_code == 200 and '"replicas": 3' in exp.text


def test_get_specific_version(client):
    s_id, e_id = _seed_service_and_env(client, "users", "dev")
    cfg = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "dev", "content": "v: 1\n"
    }).json()
    v1 = client.get(f"/configs/{cfg['id']}/versions/1")
    assert v1.status_code == 200 and v1.json()["content"] == "v: 1\n"


def test_environment_crud(client):
    e = client.post("/environments", json={"name": "qa", "namespace": "ns-qa"})
    assert e.status_code == 201
    assert len(client.get("/environments").json()) == 1
    assert client.delete(f"/environments/{e.json()['id']}").status_code == 204
    assert client.delete(f"/environments/{e.json()['id']}").status_code == 404


def test_subscriber_crud(client):
    sub = client.post("/subscribers", json={"name": "sse1", "channel": "sse", "endpoint": "/events"})
    assert sub.status_code == 201
    assert len(client.get("/subscribers").json()) == 1
    assert client.delete(f"/subscribers/{sub.json()['id']}").status_code == 204
    assert client.delete(f"/subscribers/{sub.json()['id']}").status_code == 404


def test_service_not_found_404(client):
    assert client.get("/services/999").status_code == 404


def test_rollback_missing_version_404(client):
    s_id, e_id = _seed_service_and_env(client, "rb-svc", "dev")
    cfg = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "dev", "content": "a: 1\n"
    }).json()
    assert client.post(f"/configs/{cfg['id']}/rollback", json={"version_number": 99, "author": "a"}).status_code == 404


def test_fetch_missing_404(client):
    assert client.get("/fetch/no-such-svc/prod").status_code == 404


def test_duplicate_env_409(client):
    client.post("/environments", json={"name": "dev", "namespace": "ns"})
    assert client.post("/environments", json={"name": "dev", "namespace": "ns2"}).status_code == 409


def test_duplicate_config_pair_409(client):
    s_id, e_id = _seed_service_and_env(client, "dup-svc", "dev")
    payload = {"service_id": s_id, "environment_id": e_id, "format": "yaml", "author": "a", "content": "x: 1\n"}
    assert client.post("/configs", json=payload).status_code == 201
    assert client.post("/configs", json=payload).status_code == 409


def test_unknown_schema_422(client):
    s_id, e_id = _seed_service_and_env(client, "sch-svc", "dev")
    r = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "schema_ref": "nonexistent-v9", "author": "a", "content": "x: 1\n"
    })
    assert r.status_code == 422


def test_blank_content_422(client):
    s_id, e_id = _seed_service_and_env(client, "blk-svc", "dev")
    r = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "a", "content": "   "
    })
    assert r.status_code == 422


def test_broken_json_validate(client):
    r = client.post("/configs/validate", json={"content": "{broken", "format": "json"})
    assert r.status_code == 200 and r.json()["valid"] is False


def test_port_boundaries(client):
    for port, expected in [(0, False), (1, True), (65535, True), (70000, False)]:
        r = client.post("/configs/validate", json={
            "content": f"db:\n  host: h\n  port: {port}\n",
            "format": "yaml", "schema_ref": "database-v1"
        })
        assert r.json()["valid"] is expected


def test_many_sequential_versions_and_rollback(client):
    svc_id, env_id = _seed_service_and_env(client, "version-stress", "prod")
    cfg = client.post("/configs", json={
        "service_id": svc_id, "environment_id": env_id,
        "format": "yaml", "content": "step: 1\n", "author": "bot",
    }).json()
    for step in range(2, 16):
        r = client.put(f"/configs/{cfg['id']}", json={"content": f"step: {step}\n", "author": "bot"})
        assert r.status_code == 200 and r.json()["current_version"] == step
    rb = client.post(f"/configs/{cfg['id']}/rollback", json={"version_number": 1, "author": "admin"})
    assert rb.status_code == 200 and rb.json()["current_version"] == 16


def test_failed_webhook_does_not_break_config_update(client):
    svc_id, env_id = _seed_service_and_env(client, "resilient-svc", "prod")
    client.post("/subscribers", json={
        "name": "dead-hook", "channel": "webhook",
        "endpoint": "http://127.0.0.1:1/unreachable", "service_id": svc_id,
    })
    cfg = client.post("/configs", json={
        "service_id": svc_id, "environment_id": env_id,
        "format": "yaml", "content": "mode: safe\n", "author": "dev",
    })
    assert cfg.status_code == 201
    assert any(n["status"] == "failed" and n["error"] for n in client.get("/notifications").json())
