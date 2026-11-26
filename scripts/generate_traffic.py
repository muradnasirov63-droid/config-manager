"""Генератор тестового трафика для заполнения графиков Prometheus и Grafana (ЛР№4)."""
import time
import httpx

BASE = "http://localhost:8000"


def main():
    c = httpx.Client(base_url=BASE, timeout=5.0)
    s = c.post("/services", json={"name": "billing-svc", "owner": "team-core"})
    svc_id = s.json()["id"] if s.status_code == 201 else c.get("/services").json()[0]["id"]
    e = c.post("/environments", json={"name": "prod", "namespace": "core-prod"})
    env_id = e.json()["id"] if e.status_code == 201 else c.get("/environments").json()[0]["id"]
    c.post("/subscribers", json={"name": "ops-mail", "channel": "email", "endpoint": "ops@local", "service_id": svc_id})
    cfg = c.post("/configs", json={
        "service_id": svc_id, "environment_id": env_id, "format": "yaml",
        "schema_ref": "database-v1", "author": "bot",
        "content": "db:\n  host: db-0\n  port: 5432\n"
    })
    cfg_id = cfg.json()["id"] if cfg.status_code == 201 else 1

    for i in range(1, 31):
        r1 = c.get("/services")
        r2 = c.put(f"/configs/{cfg_id}", json={"content": f"db:\n  host: db-{i}\n  port: 5432\n", "author": "bot"})
        r3 = c.get("/fetch/billing-svc/prod")
        r4 = c.post("/configs/validate", json={"content": "db:\n  host: x\n  port: 5432\n", "schema_ref": "database-v1"})
        r5 = c.put(f"/configs/{cfg_id}", json={"content": "db:\n  host: x\n  port: 70000\n", "author": "bot"})
        r6 = c.get("/configs/9999")
        print(f"Серия {i:02d}/30: GET={r1.status_code}, PUT={r2.status_code}, FETCH={r3.status_code}, VAL={r4.status_code}, BAD={r5.status_code}, 404={r6.status_code}")
        time.sleep(0.2)


if __name__ == "__main__":
    main()
