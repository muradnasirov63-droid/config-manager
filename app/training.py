"""Сбор данных и обучение модели цифрового двойника Config Manager (ЛР№5)."""
import json
import random
import time
from pathlib import Path
from typing import Any

from app.predictor import FEATURES

TARGET = "processing_time_ms"


def _make_yaml_config(num_keys: int, nesting_depth: int) -> str:
    """Генерирует валидный вложенный YAML-документ с заданным числом ключей и глубиной."""
    import yaml

    root: dict = {}
    for i in range(num_keys):
        cur = root
        max_steps = min(nesting_depth - 1, i % nesting_depth)
        for d in range(max_steps):
            node_key = f"sec_{d}"
            if node_key not in cur or not isinstance(cur[node_key], dict):
                cur[node_key] = {}
            cur = cur[node_key]
        cur[f"key_{i}"] = f"value_{i}"
    return yaml.safe_dump(root, sort_keys=False)

def build_dataset(n_samples: int = 1000, measure: bool = True, seed: int = 42) -> Any:
    """Строит датасет из n_samples примеров.
    measure=True  — реальный замер парсинга PyYAML + моделирование рассылки подписчикам;
    measure=False — быстрая формула с гауссовым шумом (для unit-тестов).
    """
    import pandas as pd

    rng = random.Random(seed)
    rows = []

    for _ in range(n_samples):
        num_keys = rng.randint(5, 500)
        nesting_depth = rng.randint(1, 10)
        num_subscribers = rng.randint(0, 50)

        if measure:
            import yaml
            doc = _make_yaml_config(num_keys, nesting_depth)
            samples = []
            for _ in range(3):
                start = time.perf_counter()
                yaml.safe_load(doc)
                samples.append((time.perf_counter() - start) * 1000)
            parse_ms = min(samples)
            elapsed = (
                1.5
                + parse_ms
                + 0.45 * nesting_depth
                + 0.35 * num_subscribers
                + rng.gauss(0, 0.8)
            )
        else:
            elapsed = (
                2.0
                + 0.04 * num_keys
                + 0.55 * nesting_depth
                + 0.38 * num_subscribers
                + rng.gauss(0, 0.6)
            )

        rows.append(
            {
                "num_keys": num_keys,
                "nesting_depth": nesting_depth,
                "num_subscribers": num_subscribers,
                TARGET: max(0.5, elapsed),
            }
        )

    return pd.DataFrame(rows)


def train(df: Any, out_dir: Path) -> tuple[dict[str, Any], Any, Any]:
    """Обучает линейную регрессию (80/20), считает R2/MAE/RMSE и CV=5."""
    import joblib
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import cross_val_score, train_test_split

    out_dir.mkdir(parents=True, exist_ok=True)
    x, y = df[FEATURES], df[TARGET]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, shuffle=True
    )

    model = LinearRegression().fit(x_train, y_train)
    predicted = model.predict(x_test)

    metrics = {
        "n_samples": len(df),
        "n_train": len(x_train),
        "n_test": len(x_test),
        "r2_train": float(r2_score(y_train, model.predict(x_train))),
        "r2_test": float(r2_score(y_test, predicted)),
        "r2_cross_validation": float(
            cross_val_score(LinearRegression(), x, y, cv=5, scoring="r2").mean()
        ),
        "mae_ms": float(mean_absolute_error(y_test, predicted)),
        "rmse_ms": float(mean_squared_error(y_test, predicted) ** 0.5),
        "coefficients": {name: float(c) for name, c in zip(FEATURES, model.coef_)},
        "intercept": float(model.intercept_),
    }

    joblib.dump(model, out_dir / "time_model.joblib")
    df.to_csv(out_dir / "dataset.csv", index=False)
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metrics, y_test, predicted


def plot_predicted_vs_actual(y_test: Any, predicted: Any, path: Path) -> None:
    """Сохраняет график «Предсказания против фактических значений»."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = float(max(y_test.max(), predicted.max()))
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(y_test, predicted, s=14, alpha=0.6)
    ax.plot([0, top], [0, top], color="red", linewidth=1.2, label="Идеальный прогноз")
    ax.set_xlabel("Фактическое время обработки, мс")
    ax.set_ylabel("Прогноз модели, мс")
    ax.set_title("Цифровой двойник Config Manager: прогноз vs факт")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
