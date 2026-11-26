"""Базовые 14 тестов API из ЛР№3."""

def _seed(client):
    s = client.post("/services", json={"name": "auth-service", "owner": "team-auth"}).json()
    e = client.post("/environments", json={"name": "dev", "namespace": "auth-dev"}).json()
    return s["id"], e["id"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_create_and_list_services(client):
    r = client.post("/services", json={"name": "auth-service", "owner": "team-auth"})
    assert r.status_code == 201
    assert len(client.get("/services").json()) == 1


def test_duplicate_service_409(client):
    client.post("/services", json={"name": "auth-service", "owner": "team-auth"})
    r = client.post("/services", json={"name": "auth-service", "owner": "team-auth"})
    assert r.status_code == 409


def test_invalid_service_name_422(client):
    r = client.post("/services", json={"name": "BAD NAME!", "owner": "team"})
    assert r.status_code == 422


def test_create_config_v1(client):
    s_id, e_id = _seed(client)
    r = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "schema_ref": "database-v1", "author": "ivanov",
        "content": "db:\n  host: localhost\n  port: 5432\n"
    })
    assert r.status_code == 201 and r.json()["current_version"] == 1


def test_update_config_creates_v2(client):
    s_id, e_id = _seed(client)
    cfg = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "ivanov", "content": "a: 1\n"
    }).json()
    r = client.put(f"/configs/{cfg['id']}", json={"content": "a: 2\n", "author": "petrov"})
    assert r.status_code == 200 and r.json()["current_version"] == 2
    assert len(client.get(f"/configs/{cfg['id']}/versions").json()) == 2


def test_get_missing_config_404(client):
    assert client.get("/configs/999").status_code == 404


def test_validate_valid_yaml(client):
    r = client.post("/configs/validate", json={
        "content": "db:\n  host: localhost\n  port: 5432\n",
        "format": "yaml", "schema_ref": "database-v1"
    })
    assert r.status_code == 200 and r.json()["valid"] is True


def test_validate_invalid_port(client):
    r = client.post("/configs/validate", json={
        "content": "db:\n  host: localhost\n  port: 70000\n",
        "format": "yaml", "schema_ref": "database-v1"
    })
    assert r.status_code == 200 and r.json()["valid"] is False


def test_validate_broken_yaml(client):
    r = client.post("/configs/validate", json={"content": "a: [1, 2", "format": "yaml"})
    assert r.status_code == 200 and r.json()["valid"] is False


def test_rollback_creates_new_version(client):
    s_id, e_id = _seed(client)
    cfg = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "a", "content": "x: 1\n"
    }).json()
    client.put(f"/configs/{cfg['id']}", json={"content": "x: 2\n", "author": "b"})
    rb = client.post(f"/configs/{cfg['id']}/rollback", json={"version_number": 1, "author": "admin"})
    assert rb.status_code == 200 and rb.json()["current_version"] == 3


def test_diff_versions(client):
    s_id, e_id = _seed(client)
    cfg = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "a", "content": "host: a\n"
    }).json()
    client.put(f"/configs/{cfg['id']}", json={"content": "host: b\n", "author": "b"})
    r = client.get(f"/configs/{cfg['id']}/diff", params={"from_version": 1, "to_version": 2})
    assert r.status_code == 200 and any("+host: b" in line for line in r.json()["diff"])


def test_fetch_actual_config(client):
    s_id, e_id = _seed(client)
    client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "a", "content": "k: v\n"
    })
    r = client.get("/fetch/auth-service/dev")
    assert r.status_code == 200 and r.json()["version"] == 1


def test_notification_sent_and_delete(client):
    s_id, e_id = _seed(client)
    client.post("/subscribers", json={
        "name": "mail-sub", "channel": "email", "endpoint": "dev@local", "service_id": s_id
    })
    cfg = client.post("/configs", json={
        "service_id": s_id, "environment_id": e_id, "format": "yaml",
        "author": "a", "content": "k: v\n"
    }).json()
    notes = client.get("/notifications").json()
    assert len(notes) == 1 and notes[0]["status"] == "sent"
    assert client.delete(f"/configs/{cfg['id']}").status_code == 204
