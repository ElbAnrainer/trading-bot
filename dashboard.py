from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from config import get_active_profile_name, get_trading_config
from performance import analyze_performance
from portfolio_state import load_portfolio_state, portfolio_summary
from risk import risk_summary


REPORTS_DIR = "reports"
DASHBOARD_JSON = os.path.join(REPORTS_DIR, "dashboard_latest.json")
DASHBOARD_HTML = os.path.join(REPORTS_DIR, "dashboard_latest.html")


def _ensure_reports_dir() -> None:
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _safe_history_tail(state: dict[str, Any], n: int = 8) -> list[dict[str, Any]]:
    history = state.get("history", [])
    if not isinstance(history, list):
        return []
    return history[-n:]


def build_documentation_section() -> dict[str, Any]:
    profile_name = get_active_profile_name()
    cfg = get_trading_config(profile_name)

    return {
        "system": "Trading Bot",
        "profile": profile_name,
        "description": "Regelbasiertes Trading-System mit Risikosteuerung",
        "risk_management": {
            "risk_per_trade": cfg.get("risk_per_trade_pct", 0.0),
            "max_portfolio_risk": cfg.get("max_portfolio_risk_pct", 0.0),
            "max_positions": cfg.get("max_positions", 0),
            "stop_loss_pct": cfg.get("stop_loss_pct", 0.0),
            "trailing_stop_pct": cfg.get("trailing_stop_pct", 0.0),
        },
        "anti_overtrading": {
            "min_hold": cfg.get("min_hold_bars", 0),
            "cooldown": cfg.get("cooldown_bars", 0),
            "max_trades_week": cfg.get("max_new_trades_per_week", 0),
            "min_expected_edge_pct": cfg.get("min_expected_edge_pct", 0.0),
        },
        "strategy": {
            "entry": "Momentum + Score + Edge",
            "exit": "Stop-Loss / Trailing Stop / Sell-Signal",
            "adaptive": "Volatilitätsbasierte Stops und risikobasierte Positionsgröße",
        },
    }


def build_dashboard_data(initial_cash: float = 1000.0) -> dict[str, Any]:
    perf = analyze_performance()
    state = load_portfolio_state(initial_cash=initial_cash)
    summary = portfolio_summary(state)
    risk = risk_summary()

    active_profile = get_active_profile_name()
    profile_cfg = get_trading_config(active_profile)

    ranking = perf.get("ranking", [])
    portfolio = perf.get("portfolio", [])
    history_tail = _safe_history_tail(state, n=8)

    total_equity = float(state.get("last_equity_eur", summary.get("cash_eur", initial_cash)))
    peak_equity = float(state.get("peak_equity_eur", total_equity))

    drawdown_pct = 0.0
    if peak_equity > 0:
        drawdown_pct = ((peak_equity - total_equity) / peak_equity) * 100.0

    return {
        "timestamp": datetime.now().isoformat(),
        "profile": {
            "name": active_profile,
            "config": profile_cfg,
        },
        "performance": {
            "closed_trades": perf.get("closed_trades", 0),
            "winning_trades": perf.get("winning_trades", 0),
            "losing_trades": perf.get("losing_trades", 0),
            "hit_rate": perf.get("hit_rate", 0.0),
            "realized_pnl": perf.get("realized_pnl", 0.0),
            "avg_trade_pnl": perf.get("avg_trade_pnl", 0.0),
            "ranking": ranking[:10],
            "portfolio_plan": portfolio[:10],
        },
        "state": {
            "cash_eur": summary.get("cash_eur", 0.0),
            "positions": summary.get("positions", 0),
            "total_invested_eur": summary.get("total_invested_eur", 0.0),
            "peak_equity_eur": peak_equity,
            "last_equity_eur": total_equity,
            "drawdown_pct": drawdown_pct,
            "updated_at": state.get("updated_at"),
            "history_tail": history_tail,
            "open_positions": state.get("positions", {}),
        },
        "risk": risk,
        "documentation": build_documentation_section(),
    }


def _write_dashboard_json(data: dict[str, Any]) -> None:
    _ensure_reports_dir()
    with open(DASHBOARD_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _html_escape(value: Any) -> str:
    import html
    return html.escape(str(value if value is not None else "-"))


def _write_dashboard_html(data: dict[str, Any]) -> None:
    _ensure_reports_dir()

    profile = data["profile"]
    perf = data["performance"]
    state = data["state"]
    risk = data["risk"]
    doc = data["documentation"]

    ranking_rows = []
    for row in perf.get("ranking", []):
        bonus_text = f"{float(row.get('bonus', 0.0)):+.2f}" if "bonus" in row else "-"
        hit_rate_text = f"{float(row.get('hit_rate', 0.0)):.2f}%"
        avg_pnl_text = f"{float(row.get('avg_pnl', 0.0)):,.2f}"
        learned_score_text = f"{float(row.get('learned_score', 0.0)):.2f}"
        ranking_rows.append(
            "<tr>"
            f"<td>{_html_escape(row.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(row.get('isin', '-'))}</td>"
            f"<td>{_html_escape(row.get('wkn', '-'))}</td>"
            f"<td style='text-align:right'>{_html_escape(bonus_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(hit_rate_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(avg_pnl_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(row.get('trades', 0))}</td>"
            f"<td style='text-align:right'>{_html_escape(learned_score_text)}</td>"
            "</tr>"
        )

    if not ranking_rows:
        ranking_rows.append("<tr><td colspan='8'>Keine Ranking-Daten vorhanden.</td></tr>")

    portfolio_rows = []
    for row in perf.get("portfolio_plan", []):
        weight_text = f"{float(row.get('weight', 0.0)):.2f}"
        capital_text = f"{float(row.get('capital', 0.0)):,.2f} EUR"
        learned_score_text = f"{float(row.get('learned_score', 0.0)):.2f}"
        portfolio_rows.append(
            "<tr>"
            f"<td>{_html_escape(row.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(row.get('isin', '-'))}</td>"
            f"<td>{_html_escape(row.get('wkn', '-'))}</td>"
            f"<td style='text-align:right'>{_html_escape(weight_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(capital_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(learned_score_text)}</td>"
            "</tr>"
        )

    if not portfolio_rows:
        portfolio_rows.append("<tr><td colspan='6'>Kein Portfolio-Plan verfügbar.</td></tr>")

    history_rows = []
    for item in state.get("history_tail", []):
        info = item.get("reason")
        if info is None and "pnl_eur" in item:
            info = f"P/L {float(item.get('pnl_eur', 0.0)):.2f} EUR"

        price_value = item.get("price")
        price_text = "-"
        if price_value is not None:
            try:
                price_text = f"{float(price_value):.2f}"
            except Exception:
                price_text = str(price_value)

        history_rows.append(
            "<tr>"
            f"<td>{_html_escape(item.get('time', '-'))}</td>"
            f"<td>{_html_escape(item.get('type', '-'))}</td>"
            f"<td>{_html_escape(item.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(item.get('isin', '-'))}</td>"
            f"<td>{_html_escape(item.get('wkn', '-'))}</td>"
            f"<td style='text-align:right'>{_html_escape(price_text)}</td>"
            f"<td>{_html_escape(info or '-')}</td>"
            "</tr>"
        )

    if not history_rows:
        history_rows.append("<tr><td colspan='7'>Keine Events vorhanden.</td></tr>")

    cfg = profile.get("config", {})

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Trading Dashboard</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 32px;
      background: #f5f7fb;
      color: #1f2937;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    .card {{
      background: white;
      border-radius: 14px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      padding: 24px;
      margin-bottom: 20px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}
    .kpi {{
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 16px;
    }}
    .label {{
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 6px;
    }}
    .value {{
      font-size: 28px;
      font-weight: bold;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid #e5e7eb;
    }}
    th {{
      color: #6b7280;
      font-size: 13px;
      text-transform: uppercase;
    }}
    .muted {{
      color: #6b7280;
    }}
    .mono {{
      font-family: Menlo, Consolas, monospace;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Trading Dashboard</h1>
      <p class="muted">Nur Simulation • Keine echten Orders • Keine Anlageberatung</p>
      <p class="muted">Letztes Update: {_html_escape(state.get('updated_at') or data.get('timestamp'))}</p>
    </div>

    <div class="card">
      <h2>Aktives Profil</h2>
      <p><strong>{_html_escape(profile.get('name', '-'))}</strong></p>
      <p class="mono">
        max_positions={_html_escape(cfg.get('max_positions'))},
        min_hold={_html_escape(cfg.get('min_hold_bars'))},
        cooldown={_html_escape(cfg.get('cooldown_bars'))},
        max_trades_week={_html_escape(cfg.get('max_new_trades_per_week'))},
        min_edge={_html_escape(cfg.get('min_expected_edge_pct'))}
      </p>
    </div>

    <div class="card">
      <h2>System-Dokumentation</h2>
      <p>{_html_escape(doc.get('description', '-'))}</p>
      <p><strong>Entry:</strong> {_html_escape(doc.get('strategy', {}).get('entry', '-'))}</p>
      <p><strong>Exit:</strong> {_html_escape(doc.get('strategy', {}).get('exit', '-'))}</p>
      <p><strong>Stops:</strong> {_html_escape(doc.get('strategy', {}).get('adaptive', '-'))}</p>
      <p class="mono">
        risk/trade={_html_escape(doc.get('risk_management', {}).get('risk_per_trade'))},
        max_portfolio_risk={_html_escape(doc.get('risk_management', {}).get('max_portfolio_risk'))},
        min_hold={_html_escape(doc.get('anti_overtrading', {}).get('min_hold'))},
        cooldown={_html_escape(doc.get('anti_overtrading', {}).get('cooldown'))}
      </p>
    </div>

    <div class="card">
      <h2>Kennzahlen</h2>
      <div class="grid">
        <div class="kpi"><div class="label">Cash</div><div class="value">{float(state['cash_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Investiert</div><div class="value">{float(state['total_invested_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Equity</div><div class="value">{float(state['last_equity_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Peak Equity</div><div class="value">{float(state['peak_equity_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Drawdown</div><div class="value">{float(state['drawdown_pct']):.2f}%</div></div>
        <div class="kpi"><div class="label">Trefferquote</div><div class="value">{float(perf['hit_rate']):.2f}%</div></div>
      </div>
    </div>

    <div class="card">
      <h2>Risk</h2>
      <p>Max Position: {float(risk.get('max_position_pct', 0.0)) * 100:.0f}% | Stop-Loss: {float(risk.get('stop_loss_pct', 0.0)) * 100:.0f}% | Trailing Stop: {float(risk.get('trailing_stop_pct', 0.0)) * 100:.0f}% | Max Drawdown: {float(risk.get('max_drawdown_pct', 0.0)) * 100:.0f}%</p>
    </div>

    <div class="card">
      <h2>Top Scores</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Bonus</th>
            <th>Treffer</th>
            <th>Ø P/L</th>
            <th>Trades</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {''.join(ranking_rows)}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Portfolio-Plan</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Gewicht</th>
            <th>Kapital</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {''.join(portfolio_rows)}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Letzte Events</h2>
      <table>
        <thead>
          <tr>
            <th>Zeit</th>
            <th>Typ</th>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Preis</th>
            <th>Info</th>
          </tr>
        </thead>
        <tbody>
          {''.join(history_rows)}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""

    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(html)


def build_dashboard(initial_cash: float = 1000.0) -> dict[str, Any]:
    """
    Kompatibel zu analysis_engine.py:
    Baut Dashboard-Daten und schreibt JSON + HTML.
    """
    data = build_dashboard_data(initial_cash=initial_cash)
    _write_dashboard_json(data)
    _write_dashboard_html(data)
    return data
