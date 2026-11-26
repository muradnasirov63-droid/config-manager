"""HTML-страница визуализации цифрового двойника (/predict/view)."""

PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>Цифровой двойник Config Manager</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 820px; margin: 24px auto; padding: 0 16px; color: #222; }
    .controls { display: flex; gap: 12px; flex-wrap: wrap; align-items: end; margin: 16px 0; }
    label { display: flex; flex-direction: column; font-size: 14px; gap: 4px; }
    input { width: 110px; padding: 6px; font-size: 15px; }
    button { padding: 8px 18px; font-size: 15px; cursor: pointer; background: #2563eb; color: #fff; border: none; border-radius: 4px; }
    #result { font-size: 18px; font-weight: bold; margin: 12px 0; }
    canvas { border: 1px solid #ccc; width: 100%; height: auto; background: #fff; }
    .hint { font-size: 13px; color: #555; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>Прогноз времени обработки конфигурации</h1>
  <p>Цифровой двойник (линейная регрессия) предсказывает время валидации, сохранения версии и рассылки уведомлений.</p>
  <div class="controls">
    <label>Ключей (Т1) <input id="keys" type="number" value="150" min="1" max="2000" /></label>
    <label>Глубина (Т2) <input id="depth" type="number" value="4" min="1" max="20" /></label>
    <label>Подписчиков (Т3) <input id="subs" type="number" value="10" min="0" max="200" /></label>
    <button onclick="runPredict()">Прогноз</button>
  </div>
  <div id="result">Загрузка...</div>
  <canvas id="chart" width="780" height="420"></canvas>
  <div class="hint">Серые точки — обучающие данные. Синяя линия — прогноз модели при росте нагрузки. Красная точка — ваш текущий прогноз.</div>

  <script>
    async function runPredict() {
      const k = +document.getElementById('keys').value;
      const d = +document.getElementById('depth').value;
      const s = +document.getElementById('subs').value;

      const [predRes, curveRes, dataRes] = await Promise.all([
        fetch('/predict', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({num_keys: k, nesting_depth: d, num_subscribers: s})
        }),
        fetch(`/predict/curve?num_keys=${k}&nesting_depth=${d}&num_subscribers=${s}`),
        fetch('/predict/data')
      ]);

      const pred = await predRes.json();
      const curve = await curveRes.json();
      const data = await dataRes.json();

      document.getElementById('result').textContent =
        `Прогноз: ${pred.predicted_time_ms} мс (ключей: ${k}, глубина: ${d}, подписчиков: ${s})`;

      drawChart(data, curve, {x: k + d * 10 + s * 5, y: pred.predicted_time_ms});
    }

    function drawChart(data, curve, current) {
      const c = document.getElementById('chart');
      const ctx = c.getContext('2d');
      ctx.clearRect(0, 0, c.width, c.height);

      const pad = 55;
      const allX = [...data.map(p => p.x), ...curve.map(p => p.x), current.x];
      const allY = [...data.map(p => p.y), ...curve.map(p => p.y), current.y];
      const maxX = Math.max(...allX) * 1.05;
      const maxY = Math.max(...allY) * 1.1;

      const tx = x => pad + (x / maxX) * (c.width - pad - 20);
      const ty = y => c.height - pad - (y / maxY) * (c.height - pad - 20);

      ctx.strokeStyle = '#333';
      ctx.beginPath();
      ctx.moveTo(pad, 20); ctx.lineTo(pad, c.height - pad); ctx.lineTo(c.width - 20, c.height - pad);
      ctx.stroke();

      ctx.fillStyle = '#333'; ctx.font = '12px Arial';
      ctx.fillText('Индекс сложности (ключи + 10*глубина + 5*подписчики)', c.width / 2 - 150, c.height - 15);
      ctx.save(); ctx.translate(16, c.height / 2 + 50); ctx.rotate(-Math.PI / 2);
      ctx.fillText('Время обработки, мс', 0, 0); ctx.restore();

      ctx.fillStyle = 'rgba(120, 120, 120, 0.45)';
      for (const p of data) {
        ctx.beginPath(); ctx.arc(tx(p.x), ty(p.y), 2.5, 0, Math.PI * 2); ctx.fill();
      }

      ctx.strokeStyle = '#2563eb'; ctx.lineWidth = 2;
      ctx.beginPath();
      curve.forEach((p, idx) => idx === 0 ? ctx.moveTo(tx(p.x), ty(p.y)) : ctx.lineTo(tx(p.x), ty(p.y)));
      ctx.stroke();

      ctx.fillStyle = '#dc2626';
      ctx.beginPath(); ctx.arc(tx(current.x), ty(current.y), 6, 0, Math.PI * 2); ctx.fill();
    }

    runPredict();
  </script>
</body>
</html>
"""
