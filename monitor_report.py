import json
import os
from datetime import datetime

from config import LOGS_DIR, MONITOR_HTML, STATUS_JSON
OUTPUT_HTML = MONITOR_HTML


def _load_status():
    if not os.path.exists(STATUS_JSON):
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "UNKNOWN",
            "ok_count": 0,
            "warn_count": 0,
            "fail_count": 0,
            "log_file": "",
        }

    with open(STATUS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _status_color(status):
    mapping = {
        "GREEN": "#15803d",
        "YELLOW": "#ca8a04",
        "RED": "#b91c1c",
        "UNKNOWN": "#374151",
    }
    return mapping.get(status, "#374151")


def _status_text(status):
    mapping = {
        "GREEN": "GRÜN – alles ok",
        "YELLOW": "GELB – Warnungen vorhanden",
        "RED": "ROT – Fehler vorhanden",
        "UNKNOWN": "UNBEKANNT",
    }
    return mapping.get(status, status)


def build_monitor_report():
    status = _load_status()
    color = _status_color(status["status"])
    status_text = _status_text(status["status"])

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>Monitoring Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 32px;
            background: #f5f7fb;
            color: #1f2937;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        .card {{
            background: white;
            border-radius: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            padding: 24px;
            margin-bottom: 20px;
        }}
        .status {{
            display: inline-block;
            padding: 10px 18px;
            border-radius: 999px;
            color: white;
            font-weight: bold;
            background: {color};
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-top: 18px;
        }}
        .kpi {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 18px;
        }}
        .kpi .label {{
            color: #6b7280;
            font-size: 13px;
            margin-bottom: 6px;
        }}
        .kpi .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .muted {{
            color: #6b7280;
        }}
        code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 6px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Monitoring Report</h1>
            <p class="muted">Automatischer Gesundheitscheck des Projekts</p>
            <div class="status">{status_text}</div>
            <p class="muted" style="margin-top:16px;">Letzter Lauf: {status["timestamp"]}</p>
        </div>

        <div class="card">
            <h2>Zusammenfassung</h2>
            <div class="grid">
                <div class="kpi">
                    <div class="label">OK</div>
                    <div class="value">{status["ok_count"]}</div>
                </div>
                <div class="kpi">
                    <div class="label">Warnungen</div>
                    <div class="value">{status["warn_count"]}</div>
                </div>
                <div class="kpi">
                    <div class="label">Fehler</div>
                    <div class="value">{status["fail_count"]}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Dateien</h2>
            <p>Aktueller Status als JSON: <code>{STATUS_JSON}</code></p>
            <p>Aktuelles Log: <code>{status.get("log_file", "")}</code></p>
            <p class="muted">Tipp: Öffne zusätzlich <code>{os.path.join(LOGS_DIR, "check_current_latest.log")}</code> für Details.</p>
        </div>
    </div>
</body>
</html>
"""

    os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Monitoring HTML erstellt: {OUTPUT_HTML}")


if __name__ == "__main__":
    build_monitor_report()
