import csv
import os

JOURNAL_FILE = "reports/trading_journal.csv"
OUTPUT_FILE = "reports/dashboard.html"


def build_dashboard():
    rows = []

    try:
        with open(JOURNAL_FILE, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        rows = []

    os.makedirs("reports", exist_ok=True)

    if not rows:
        html = """
<html>
<head>
    <meta charset="utf-8">
    <title>Paper-Trading-Dashboard</title>
</head>
<body>
    <h1>Paper-Trading-Dashboard</h1>
    <p>Keine Daten im Simulationsjournal vorhanden.</p>
    <p><strong>Hinweis:</strong> Dies ist nur eine Simulation. Es werden keine echten Orders ausgeführt.</p>
</body>
</html>
"""
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return

    signals = [row.get("signal", "") for row in rows]
    buy_count = signals.count("BUY")
    sell_count = signals.count("SELL")
    watch_count = signals.count("WATCH")
    hold_count = signals.count("HOLD")

    recent_items = rows[-20:]

    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>Paper-Trading-Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 30px;
            background: #f7f7f7;
            color: #222;
        }}
        h1, h2 {{
            margin-bottom: 10px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }}
        ul {{
            line-height: 1.6;
        }}
        .note {{
            background: #fff3cd;
            border: 1px solid #ffe69c;
            border-radius: 8px;
            padding: 12px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Paper-Trading-Dashboard</h1>
        <p>Automatisch erzeugt aus <code>reports/trading_journal.csv</code>.</p>
        <div class="note">
            <strong>Wichtiger Hinweis:</strong><br>
            Dieses Dashboard dient ausschließlich der Simulation, dem Backtesting und der persönlichen Analyse.
            Es werden keine echten Orders ausgeführt und es handelt sich nicht um Anlageberatung.
        </div>
    </div>

    <div class="card">
        <h2>Signal-Verteilung</h2>
        <canvas id="pie" width="400" height="220"></canvas>
    </div>

    <div class="card">
        <h2>Letzte Beobachtungssignale</h2>
        <ul>
"""

    for row in recent_items:
        html += (
            f"<li>{row.get('timestamp', '')} | "
            f"{row.get('symbol', '')} | "
            f"{row.get('company', '')} | "
            f"{row.get('signal', '')} | "
            f"{row.get('price_eur', '')} EUR</li>"
        )

    html += f"""
        </ul>
    </div>

    <script>
        const ctx = document.getElementById('pie');
        new Chart(ctx, {{
            type: 'pie',
            data: {{
                labels: ['BUY', 'SELL', 'WATCH', 'HOLD'],
                datasets: [{{
                    data: [{buy_count}, {sell_count}, {watch_count}, {hold_count}]
                }}]
            }}
        }});
    </script>
</body>
</html>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
