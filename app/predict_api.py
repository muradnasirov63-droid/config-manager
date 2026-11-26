"""Маршруты цифрового двойника: /predict, данные для графика и /predict/view (ЛР№5)."""
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.predict_page import PAGE
from app.predictor import ModelNotReadyError, model_path, predict_time_ms

router = APIRouter(tags=["digital-twin"])


class PredictRequest(BaseModel):
    num_keys: int = Field(ge=1, le=2000, description="Число ключей в конфигурации (Т1)", examples=[150])
    nesting_depth: int = Field(ge=1, le=20, description="Глубина вложенности YAML/JSON (Т2)", examples=[4])
    num_subscribers: int = Field(ge=0, le=200, description="Число подписчиков уведомлений (Т3)", examples=[10])


class PredictResponse(BaseModel):
    predicted_time_ms: float


def _predict(num_keys: int, nesting_depth: int, num_subscribers: int) -> float:
    try:
        return predict_time_ms(num_keys, nesting_depth, num_subscribers)
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict", response_model=PredictResponse)
def predict(data: PredictRequest) -> PredictResponse:
    # create endpoint for prediction using the model
    value = _predict(data.num_keys, data.nesting_depth, data.num_subscribers)
    return PredictResponse(predicted_time_ms=round(value, 3))


@router.get("/predict/curve")
def curve(
    num_keys: Annotated[int, Query(ge=1, le=2000)] = 150,
    nesting_depth: Annotated[int, Query(ge=1, le=20)] = 4,
    num_subscribers: Annotated[int, Query(ge=0, le=200)] = 10,
) -> list[dict[str, float]]:
    """Линия прогноза при пропорциональном масштабировании нагрузки."""
    points = []
    for step in range(1, 31):
        scale = 0.1 * step
        k = max(1, round(num_keys * scale))
        d = max(1, round(nesting_depth * scale))
        s = max(0, round(num_subscribers * scale))
        points.append({"x": float(k + d * 10 + s * 5), "y": round(_predict(k, d, s), 3)})
    return points


@router.get("/predict/data")
def training_data() -> list[dict[str, float]]:
    """Выборка обучающих данных (до 300 точек) для визуализации."""
    import pandas as pd

    path = Path(model_path()).parent / "dataset.csv"
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail="Набор данных не найден. Выполните: python scripts/train_model.py",
        )
    df: Any = pd.read_csv(path)
    if len(df) > 300:
        df = df.sample(n=300, random_state=1)
    return [
        {
            "x": float(row["num_keys"] + row["nesting_depth"] * 10 + row["num_subscribers"] * 5),
            "y": round(float(row["processing_time_ms"]), 3),
        }
        for _, row in df.iterrows()
    ]


@router.get("/predict/view", response_class=HTMLResponse)
def view() -> str:
    """Веб-страница визуализации прогноза."""
    return PAGE
