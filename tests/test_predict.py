"""Тесты модели цифрового двойника и маршрутов /predict (ЛР№5)."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.predictor import FEATURES, _load, predict_time_ms
from app.training import TARGET, build_dataset, train


@pytest.fixture()
def trained_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, float]]:
    metrics, _, _ = train(build_dataset(300, measure=False), tmp_path)
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "time_model.joblib"))
    _load.cache_clear()
    yield metrics
    _load.cache_clear()


def test_dataset_columns() -> None:
    df = build_dataset(50, measure=False)
    assert list(df.columns) == [*FEATURES, TARGET]
    assert len(df) == 50 and (df[TARGET] > 0).all()


def test_model_quality_on_holdout(trained_model: dict[str, float]) -> None:
    assert trained_model["r2_test"] > 0.9
    assert trained_model["mae_ms"] < 1.0


def test_heavier_config_takes_longer(trained_model: dict[str, float]) -> None:
    assert predict_time_ms(400, 8, 40) > predict_time_ms(10, 1, 0)


def test_predict_endpoint_success(client: TestClient, trained_model: dict[str, float]) -> None:
    resp = client.post("/predict", json={"num_keys": 150, "nesting_depth": 4, "num_subscribers": 10})
    assert resp.status_code == 200
    assert resp.json()["predicted_time_ms"] > 0


@pytest.mark.parametrize(
    "payload",
    [
        {"num_keys": 0, "nesting_depth": 4, "num_subscribers": 10},
        {"num_keys": 50, "nesting_depth": 0, "num_subscribers": 10},
        {"num_keys": 50, "nesting_depth": 4, "num_subscribers": -1},
        {"num_keys": "много", "nesting_depth": 4, "num_subscribers": 10},
    ],
)
def test_predict_validation_errors(client: TestClient, trained_model: dict[str, float], payload: dict) -> None:
    assert client.post("/predict", json=payload).status_code == 422


def test_predict_without_model_returns_503(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "missing.joblib"))
    _load.cache_clear()
    resp = client.post("/predict", json={"num_keys": 50, "nesting_depth": 2, "num_subscribers": 1})
    assert resp.status_code == 503


def test_curve_data_and_view(client: TestClient, trained_model: dict[str, float]) -> None:
    curve = client.get("/predict/curve", params={"num_keys": 150, "nesting_depth": 4, "num_subscribers": 10}).json()
    assert len(curve) == 30 and curve[-1]["y"] > curve[0]["y"]
    data = client.get("/predict/data").json()
    assert len(data) == 300
    page = client.get("/predict/view")
    assert page.status_code == 200 and "<canvas" in page.text
