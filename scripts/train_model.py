"""Скрипт обучения модели цифрового двойника (ЛР№5)."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.training import build_dataset, plot_predicted_vs_actual, train  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "model"))
    args = parser.parse_args()

    mode = "формула" if args.synthetic else "замеры PyYAML + рассылка"
    print(f"Строю набор данных: {args.samples} примеров ({mode})...")
    df = build_dataset(args.samples, measure=not args.synthetic)
    print(df.describe().round(3).to_string())

    out_dir = Path(args.out)
    metrics, y_test, predicted = train(df, out_dir)

    print("\nМодель: линейная регрессия, выборка 80/20")
    print(f"Примеров: всего {metrics['n_samples']}, обучение {metrics['n_train']}, тест {metrics['n_test']}")
    print(f"R2 (обучение):           {metrics['r2_train']:.3f}")
    print(f"R2 (тест):               {metrics['r2_test']:.3f}")
    print(f"R2 (кросс-валидация, 5): {metrics['r2_cross_validation']:.3f}")
    print(f"MAE:                     {metrics['mae_ms']:.3f} мс")
    print(f"RMSE:                    {metrics['rmse_ms']:.3f} мс")
    print(f"Коэффициенты: {metrics['coefficients']}, свободный член: {metrics['intercept']:.3f}")

    if not args.no_plots:
        plot_path = out_dir / "pred_vs_actual.png"
        plot_predicted_vs_actual(y_test, predicted, plot_path)
        print(f"Рисунок сохранён: {plot_path}")
    print(f"Модель сохранена: {out_dir / 'time_model.joblib'}")


if __name__ == "__main__":
    main()
