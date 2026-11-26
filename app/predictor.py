"""Прогноз времени обработки обновления конфигурации по обученной модели (ЛР№5)."""
import os
from functools import lru_cache
from typing import Any

DEFAULT_MODEL_PATH = "model/time_model.joblib"
FEATURES = ["num_keys", "nesting_depth", "num_subscribers"]


class ModelNotReadyError(RuntimeError):
    """Файл обученной модели не найден."""


def model_path() -> str:
    return os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)


@lru_cache(maxsize=2)
def _load(path: str) -> Any:
    import joblib

    if not os.path.exists(path):
        raise ModelNotReadyError(
            f"Модель не найдена ({path}). Обучите её командой: python scripts/train_model.py"
        )
    return joblib.load(path)


def predict_time_ms(num_keys: int, nesting_depth: int, num_subscribers: int) -> float:
    """Возвращает прогноз времени обработки конфигурации в миллисекундах."""
    import pandas as pd

    model = _load(model_path())
    features = pd.DataFrame(
        [[num_keys, nesting_depth, num_subscribers]],
        columns=FEATURES,
    )
    return max(0.0, float(model.predict(features)[0]))
