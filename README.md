# Config Manager (вариант 15 — Система управления конфигурациями)

Централизованное хранение конфигураций микросервисов: REST API (FastAPI), версионирование,
валидация YAML/JSON по JSON Schema, уведомления об изменениях, мониторинг Prometheus/Grafana
и цифровой двойник (ЛР№5 — модель линейной регрессии, `/predict`, `/predict/view`).

## Быстрый старт (ЛР№5)
```bash
pip install -r requirements.txt
python scripts/train_model.py
python -m pytest -v
docker compose up --build -d
```

- Swagger UI: http://localhost:8000/docs
- Цифровой двойник (визуализация): http://localhost:8000/predict/view
- Метрики Prometheus: http://localhost:8000/metrics
- Prometheus UI: http://localhost:9090
- Grafana UI: http://localhost:3000 (admin / admin)
