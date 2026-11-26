"""Интеграционные тесты с testcontainers (PostgreSQL 16) из ЛР№4."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app.database import Base, get_db


@pytest.fixture(scope="module")
def postgres_url():
    tc_postgres = pytest.importorskip("testcontainers.postgres")
    try:
        container = tc_postgres.PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:
        pytest.skip(f"Docker недоступен для testcontainers: {exc}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture()
def pg_client(postgres_url):
    engine = create_engine(postgres_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    orig = main_module.SessionLocal
    main_module.SessionLocal = Session
    main_module.app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(main_module.app) as c:
            yield c
    finally:
        main_module.app.dependency_overrides.clear()
        main_module.SessionLocal = orig
        engine.dispose()


def test_postgres_connection_and_health(postgres_url, pg_client):
    with create_engine(postgres_url).connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar_one() == 1
    assert pg_client.get("/health").json() == {"status": "ok", "db": "up"}


def test_full_config_lifecycle_and_constraints_in_postgres(pg_client):
    s = pg_client.post("/services", json={"name": "pg-svc", "owner": "team"}).json()
    e = pg_client.post("/environments", json={"name": "prod", "namespace": "pg-prod"}).json()
    cfg = pg_client.post("/configs", json={
        "service_id": s["id"], "environment_id": e["id"], "format": "yaml",
        "author": "dev", "content": "a: 1\n"
    }).json()
    assert pg_client.put(f"/configs/{cfg['id']}", json={"content": "a: 2\n", "author": "dev"}).json()["current_version"] == 2
    assert pg_client.post(f"/configs/{cfg['id']}/rollback", json={"version_number": 1, "author": "adm"}).json()["current_version"] == 3
    assert pg_client.get("/fetch/pg-svc/prod").json()["version"] == 3
    dup = pg_client.post("/configs", json={
        "service_id": s["id"], "environment_id": e["id"], "format": "yaml",
        "author": "dev", "content": "a: 9\n"
    })
    assert dup.status_code == 409


def test_validation_notifications_and_metrics_in_postgres(pg_client):
    s = pg_client.post("/services", json={"name": "pg-val", "owner": "team"}).json()
    e = pg_client.post("/environments", json={"name": "dev", "namespace": "pg-dev"}).json()
    pg_client.post("/subscribers", json={"name": "m", "channel": "email", "endpoint": "a@b", "service_id": s["id"]})
    bad = pg_client.post("/configs", json={
        "service_id": s["id"], "environment_id": e["id"], "format": "yaml",
        "schema_ref": "database-v1", "author": "dev", "content": "db:\n  host: h\n  port: 99999\n"
    })
    assert bad.status_code == 422
    ok = pg_client.post("/configs", json={
        "service_id": s["id"], "environment_id": e["id"], "format": "yaml",
        "schema_ref": "database-v1", "author": "dev", "content": "db:\n  host: h\n  port: 5432\n"
    })
    assert ok.status_code == 201
    assert len(pg_client.get("/notifications").json()) == 1
    assert "config_versions_total" in pg_client.get("/metrics").text
