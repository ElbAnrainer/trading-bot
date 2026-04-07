from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from config import (
    DASHBOARD_HTML,
    DASHBOARD_JSON,
    LATEST_RUN_JSON,
    ensure_reports_dir,
    get_active_profile_name,
    get_trading_config,
)
from performance import analyze_performance
from portfolio_state import load_portfolio_state, portfolio_summary
from risk import risk_summary


def _ensure_reports_dir() -> None:
    ensure_reports_dir()


def _safe_history_tail(state: dict[str, Any], n: int = 8) -> list[dict[str, Any]]:
    history = state.get("history", [])
    if not isinstance(history, list):
        return []
    return history[-n:]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_text(value: Any, default: str = "-") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else default


def _safe_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        text = _safe_text(item, "")
        if text:
            out.append(text)
    return out


def _company_name(item: dict[str, Any]) -> str:
    return _safe_text(
        item.get("company_name") or item.get("company") or item.get("symbol"),
        "-",
    )


def _load_latest_run_snapshot() -> dict[str, Any]:
    if not os.path.exists(LATEST_RUN_JSON):
        return {}

    try:
        with open(LATEST_RUN_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}

    return {}


def _coerce_analysis_snapshot(
    analysis_result: dict[str, Any] | None,
    trading_plan: list[dict[str, Any]] | None = None,
    decisions: dict[str, Any] | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    if analysis_result is None:
        snapshot = _load_latest_run_snapshot()
        source = "latest_run"
    else:
        snapshot = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "period": analysis_result.get("period"),
            "interval": analysis_result.get("interval"),
            "profile_name": profile_name or analysis_result.get("profile_name"),
            "results": analysis_result.get("results", []),
            "portfolio": analysis_result.get("portfolio", {}),
            "future_candidates": analysis_result.get("future_candidates", []),
        }
        source = "current_run"

    if trading_plan is not None:
        snapshot["trading_plan"] = trading_plan
    if decisions is not None:
        snapshot["decisions"] = decisions

    snapshot["_source"] = source
    return snapshot


def _normalize_current_results(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in snapshot.get("results", []) or []:
        rows.append(
            {
                "symbol": _safe_text(item.get("symbol")),
                "company": _company_name(item),
                "isin": _safe_text(item.get("isin")),
                "wkn": _safe_text(item.get("wkn")),
                "signal": _safe_text(item.get("signal")),
                "native_currency": _safe_text(item.get("native_currency")),
                "pnl_eur": _safe_float(item.get("pnl_eur")),
                "pnl_native": _safe_float(item.get("pnl_native")),
                "pnl_pct_eur": _safe_float(item.get("pnl_pct_eur")),
                "trade_count": _safe_int(item.get("trade_count")),
                "hit_rate_pct": _safe_float(item.get("hit_rate_pct")),
                "score": _safe_float(item.get("score")),
                "last_price_eur": _safe_float(item.get("last_price_eur")),
                "last_price_native": _safe_float(item.get("last_price_native")),
                "explanation_summary": _safe_text(item.get("explanation_summary"), ""),
                "explanation_points": _safe_text_list(item.get("explanation_points")),
            }
        )
    return rows


def _normalize_future_candidates(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in snapshot.get("future_candidates", []) or []:
        rows.append(
            {
                "symbol": _safe_text(item.get("symbol")),
                "company": _company_name(item),
                "isin": _safe_text(item.get("isin")),
                "wkn": _safe_text(item.get("wkn")),
                "future_signal": _safe_text(item.get("future_signal")),
                "score": _safe_float(item.get("score")),
                "learned_bonus": _safe_float(item.get("learned_bonus")),
                "learned_confidence": _safe_float(item.get("learned_confidence")),
                "explanation_summary": _safe_text(item.get("explanation_summary"), ""),
                "explanation_points": _safe_text_list(item.get("explanation_points")),
            }
        )
    return rows


def _normalize_trading_plan(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in snapshot.get("trading_plan", []) or []:
        rows.append(
            {
                "symbol": _safe_text(item.get("symbol")),
                "company": _company_name(item),
                "isin": _safe_text(item.get("isin")),
                "wkn": _safe_text(item.get("wkn")),
                "signal": _safe_text(item.get("signal"), ""),
                "weight": _safe_float(item.get("weight")),
                "capital": _safe_float(item.get("capital")),
                "learned_score": _safe_float(item.get("learned_score")),
                "explanation_summary": _safe_text(item.get("explanation_summary"), ""),
                "explanation_points": _safe_text_list(item.get("explanation_points")),
            }
        )
    return rows


def _normalize_simulated_portfolio(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    portfolio = snapshot.get("portfolio", {}) or {}
    if not isinstance(portfolio, dict):
        return []

    rows = []
    for symbol, pos in portfolio.items():
        qty = _safe_float(pos.get("qty"))
        price_eur = _safe_float(pos.get("price_eur"))
        rows.append(
            {
                "symbol": _safe_text(symbol),
                "company": _company_name(pos | {"symbol": symbol}),
                "isin": _safe_text(pos.get("isin")),
                "wkn": _safe_text(pos.get("wkn")),
                "qty": qty,
                "price_eur": price_eur,
                "price_native": _safe_float(pos.get("price_native")),
                "native_currency": _safe_text(pos.get("native_currency")),
                "value_eur": qty * price_eur,
            }
        )
    return rows


def _normalize_orders(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = snapshot.get("decisions", {}) or {}
    rows = []
    for item in decisions.get("orders", []) or []:
        rows.append(
            {
                "action": _safe_text(item.get("action")),
                "symbol": _safe_text(item.get("symbol")),
                "reason": _safe_text(item.get("reason")),
                "reason_label": _safe_text(item.get("reason_label"), _safe_text(item.get("reason"))),
                "capital": _safe_float(item.get("capital")),
                "weight": _safe_float(item.get("weight")),
                "learned_score": _safe_float(item.get("learned_score")),
                "company": _company_name(item),
                "isin": _safe_text(item.get("isin")),
                "wkn": _safe_text(item.get("wkn")),
                "signal": _safe_text(item.get("signal"), ""),
                "explanation_summary": _safe_text(item.get("explanation_summary"), ""),
                "explanation_points": _safe_text_list(item.get("explanation_points")),
            }
        )
    return rows


def _build_analysis_section(
    analysis_result: dict[str, Any] | None = None,
    trading_plan: list[dict[str, Any]] | None = None,
    decisions: dict[str, Any] | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    snapshot = _coerce_analysis_snapshot(
        analysis_result,
        trading_plan=trading_plan,
        decisions=decisions,
        profile_name=profile_name,
    )

    generated_at = _safe_text(snapshot.get("generated_at_utc"), "")
    period = _safe_text(snapshot.get("period"))
    interval = _safe_text(snapshot.get("interval"))
    analysis_profile_name = _safe_text(snapshot.get("profile_name"), "")

    current_results = _normalize_current_results(snapshot)
    future_candidates = _normalize_future_candidates(snapshot)
    trading_plan_rows = _normalize_trading_plan(snapshot)
    simulated_portfolio = _normalize_simulated_portfolio(snapshot)
    orders = _normalize_orders(snapshot)

    return {
        "source": snapshot.get("_source", "none"),
        "generated_at": generated_at,
        "period": period,
        "interval": interval,
        "profile_name": analysis_profile_name,
        "current_results": current_results,
        "future_candidates": future_candidates,
        "trading_plan": trading_plan_rows,
        "simulated_portfolio": simulated_portfolio,
        "orders": orders,
        "drawdown_state": (snapshot.get("decisions") or {}).get("drawdown_state", {}),
        "risk": (snapshot.get("decisions") or {}).get("risk", {}),
    }


def build_documentation_section(profile_name: str | None = None) -> dict[str, Any]:
    profile_name = profile_name or get_active_profile_name()
    cfg = get_trading_config(profile_name)

    return {
        "system": "Trading Bot",
        "profile": profile_name,
        "description": "Regelbasiertes Trading-System mit Risikosteuerung",
        "risk_management": {
            "risk_per_trade": cfg.get("risk_per_trade_pct", 0.0),
            "max_portfolio_risk": cfg.get("max_portfolio_risk_pct", 0.0),
            "max_positions": cfg.get("max_positions", 0),
            "max_drawdown_pct": cfg.get("max_drawdown_pct", 0.0),
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


def build_dashboard_data(
    initial_cash: float = 1000.0,
    analysis_result: dict[str, Any] | None = None,
    trading_plan: list[dict[str, Any]] | None = None,
    decisions: dict[str, Any] | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    perf = analyze_performance()
    state = load_portfolio_state(initial_cash=initial_cash)
    summary = portfolio_summary(state)
    analysis = _build_analysis_section(
        analysis_result=analysis_result,
        trading_plan=trading_plan,
        decisions=decisions,
        profile_name=profile_name,
    )

    active_profile = profile_name or analysis.get("profile_name") or get_active_profile_name()
    profile_cfg = get_trading_config(active_profile)
    risk = risk_summary(active_profile)

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
        "analysis": analysis,
        "performance": {
            "total_entries": perf.get("total_entries", 0),
            "buy_signals": perf.get("buy_signals", 0),
            "sell_signals": perf.get("sell_signals", 0),
            "watch_signals": perf.get("watch_signals", 0),
            "hold_signals": perf.get("hold_signals", 0),
            "stocks_total": perf.get("stocks_total", perf.get("unique_symbols", 0)),
            "closed_trades": perf.get("closed_trades", 0),
            "winning_trades": perf.get("winning_trades", 0),
            "losing_trades": perf.get("losing_trades", 0),
            "hit_rate": perf.get("hit_rate", 0.0),
            "realized_pnl": perf.get("realized_pnl", 0.0),
            "avg_trade_pnl": perf.get("avg_trade_pnl", 0.0),
            "top_symbols": perf.get("top_symbols", []),
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
        "documentation": build_documentation_section(active_profile),
    }


def _write_dashboard_json(data: dict[str, Any]) -> None:
    _ensure_reports_dir()
    with open(DASHBOARD_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _html_escape(value: Any) -> str:
    import html

    return html.escape(str(value if value is not None else "-"))


def _analysis_source_label(source: str) -> str:
    labels = {
        "current_run": "Aktueller CLI-Lauf",
        "latest_run": "Letzter gespeicherter Lauf",
        "none": "Keine aktuelle Analyse",
    }
    return labels.get(source, source)


def _render_explanation_list(items: list[dict[str, Any]], empty_text: str) -> str:
    entries = []
    for item in items:
        summary = _safe_text(item.get("explanation_summary"), "")
        if not summary:
            continue
        points = _safe_text_list(item.get("explanation_points"))
        detail_html = ""
        if points:
            detail_html = "<div class='explanation-meta'>" + " | ".join(_html_escape(point) for point in points[:3]) + "</div>"
        entries.append(
            "<li>"
            f"<strong>{_html_escape(item.get('symbol', '-'))}</strong>: {_html_escape(summary)}"
            f"{detail_html}"
            "</li>"
        )

    if not entries:
        return f"<p class='muted'>{_html_escape(empty_text)}</p>"

    return "<ul class='explanations'>" + "".join(entries) + "</ul>"


def _write_dashboard_html(data: dict[str, Any]) -> None:
    _ensure_reports_dir()

    profile = data["profile"]
    analysis = data["analysis"]
    perf = data["performance"]
    state = data["state"]
    risk = data["risk"]
    doc = data["documentation"]

    current_result_rows = []
    for row in analysis.get("current_results", []):
        pnl_text = f"{float(row.get('pnl_eur', 0.0)):,.2f} EUR"
        score_text = f"{float(row.get('score', 0.0)):.2f}"
        current_result_rows.append(
            "<tr>"
            f"<td>{_html_escape(row.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(row.get('isin', '-'))}</td>"
            f"<td>{_html_escape(row.get('wkn', '-'))}</td>"
            f"<td>{_html_escape(row.get('company', '-'))}</td>"
            f"<td>{_html_escape(row.get('signal', '-'))}</td>"
            f"<td style='text-align:right'>{_html_escape(pnl_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(row.get('trade_count', 0))}</td>"
            f"<td style='text-align:right'>{_html_escape(score_text)}</td>"
            "</tr>"
        )

    if not current_result_rows:
        current_result_rows.append("<tr><td colspan='8'>Keine frische Analyse vorhanden.</td></tr>")

    candidate_rows = []
    for row in analysis.get("future_candidates", []):
        score_text = f"{float(row.get('score', 0.0)):.2f}"
        learned_bonus_text = f"{float(row.get('learned_bonus', 0.0)):+.2f}"
        candidate_rows.append(
            "<tr>"
            f"<td>{_html_escape(row.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(row.get('isin', '-'))}</td>"
            f"<td>{_html_escape(row.get('wkn', '-'))}</td>"
            f"<td>{_html_escape(row.get('company', '-'))}</td>"
            f"<td>{_html_escape(row.get('future_signal', '-'))}</td>"
            f"<td style='text-align:right'>{_html_escape(score_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(learned_bonus_text)}</td>"
            "</tr>"
        )

    if not candidate_rows:
        candidate_rows.append("<tr><td colspan='7'>Keine aktuellen Kaufkandidaten verfügbar.</td></tr>")

    plan_rows = []
    plan_source = analysis.get("trading_plan") or perf.get("portfolio_plan", [])
    plan_title = "Trading-Plan"
    if not analysis.get("trading_plan"):
        plan_title = "Historischer Portfolio-Plan"

    for row in plan_source:
        weight_text = f"{float(row.get('weight', 0.0)):.2f}"
        capital_text = f"{float(row.get('capital', 0.0)):,.2f} EUR"
        learned_score_text = f"{float(row.get('learned_score', 0.0)):.2f}"
        plan_rows.append(
            "<tr>"
            f"<td>{_html_escape(row.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(row.get('isin', '-'))}</td>"
            f"<td>{_html_escape(row.get('wkn', '-'))}</td>"
            f"<td>{_html_escape(row.get('company', row.get('symbol', '-')))}</td>"
            f"<td style='text-align:right'>{_html_escape(weight_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(capital_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(learned_score_text)}</td>"
            "</tr>"
        )

    if not plan_rows:
        plan_rows.append("<tr><td colspan='7'>Kein Trading-Plan verfügbar.</td></tr>")

    order_rows = []
    for row in analysis.get("orders", []):
        capital_text = f"{float(row.get('capital', 0.0)):,.2f} EUR"
        weight_text = f"{float(row.get('weight', 0.0)) * 100:.1f}%"
        learned_score_text = f"{float(row.get('learned_score', 0.0)):.2f}"
        order_rows.append(
            "<tr>"
            f"<td>{_html_escape(row.get('action', '-'))}</td>"
            f"<td>{_html_escape(row.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(row.get('reason_label', row.get('reason', '-')))}</td>"
            f"<td style='text-align:right'>{_html_escape(capital_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(weight_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(learned_score_text)}</td>"
            "</tr>"
        )

    if not order_rows:
        order_rows.append("<tr><td colspan='6'>Keine aktuellen Orders verfügbar.</td></tr>")

    simulated_portfolio_rows = []
    for row in analysis.get("simulated_portfolio", []):
        qty_text = f"{float(row.get('qty', 0.0)):.2f}"
        price_text = f"{float(row.get('price_eur', 0.0)):,.2f} EUR"
        value_text = f"{float(row.get('value_eur', 0.0)):,.2f} EUR"
        simulated_portfolio_rows.append(
            "<tr>"
            f"<td>{_html_escape(row.get('symbol', '-'))}</td>"
            f"<td>{_html_escape(row.get('isin', '-'))}</td>"
            f"<td>{_html_escape(row.get('wkn', '-'))}</td>"
            f"<td>{_html_escape(row.get('company', '-'))}</td>"
            f"<td style='text-align:right'>{_html_escape(qty_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(price_text)}</td>"
            f"<td style='text-align:right'>{_html_escape(value_text)}</td>"
            "</tr>"
        )

    if not simulated_portfolio_rows:
        simulated_portfolio_rows.append("<tr><td colspan='7'>Kein simuliertes Depot aus dem letzten Analyse-Lauf verfügbar.</td></tr>")

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
    analysis_generated_at = analysis.get("generated_at") or state.get("updated_at") or data.get("timestamp")
    analysis_source = _analysis_source_label(str(analysis.get("source", "none")))
    analysis_results_count = len(analysis.get("current_results", []))
    analysis_candidates_count = len(analysis.get("future_candidates", []))
    analysis_orders_count = len(analysis.get("orders", []))
    state_positions_count = state.get("positions", 0)
    state_updated_at = state.get("updated_at") or "-"
    result_explanations_html = _render_explanation_list(
        analysis.get("current_results", []),
        "Keine erklärbaren Details zum aktuellen Analyse-Lauf verfügbar.",
    )
    candidate_explanations_html = _render_explanation_list(
        analysis.get("future_candidates", []),
        "Keine Kandidaten-Erklärungen verfügbar.",
    )
    plan_explanations_html = _render_explanation_list(
        plan_source,
        "Kein erklärbarer Trading-Plan verfügbar.",
    )
    order_explanations_html = _render_explanation_list(
        analysis.get("orders", []),
        "Keine aktuellen Order-Erklärungen verfügbar.",
    )

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
    .explanations {{
      margin: 14px 0 0 18px;
      padding: 0;
    }}
    .explanations li {{
      margin: 0 0 10px 0;
    }}
    .explanation-meta {{
      color: #6b7280;
      font-size: 13px;
      margin-top: 4px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Trading Dashboard</h1>
      <p class="muted">Nur Simulation • Keine echten Orders • Keine Anlageberatung</p>
      <p class="muted">Letztes Update: {_html_escape(analysis_generated_at)}</p>
    </div>

    <div class="card">
      <h2>Aktueller Analyse-Lauf</h2>
      <p class="muted">Diese Werte stammen aus dem letzten frischen Analyse-Lauf und nicht aus dem historischen Journal.</p>
      <p><strong>Quelle:</strong> {_html_escape(analysis_source)}</p>
      <p><strong>Zeitraum:</strong> {_html_escape(analysis.get('period', '-'))} | <strong>Intervall:</strong> {_html_escape(analysis.get('interval', '-'))}</p>
      <p><strong>Ergebnisse:</strong> {_html_escape(analysis_results_count)} | <strong>Kandidaten:</strong> {_html_escape(analysis_candidates_count)} | <strong>Orders:</strong> {_html_escape(analysis_orders_count)}</p>
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
      <h2>Historische Performance</h2>
      <p class="muted">Diese Kennzahlen werden aus dem persistierten Journal und dem selbstlernenden Score abgeleitet.</p>
      <div class="grid">
        <div class="kpi"><div class="label">Geschlossene Trades</div><div class="value">{int(perf['closed_trades'])}</div></div>
        <div class="kpi"><div class="label">Gewinntrades</div><div class="value">{int(perf['winning_trades'])}</div></div>
        <div class="kpi"><div class="label">Verlusttrades</div><div class="value">{int(perf['losing_trades'])}</div></div>
        <div class="kpi"><div class="label">Trefferquote</div><div class="value">{float(perf['hit_rate']):.2f}%</div></div>
        <div class="kpi"><div class="label">Realisiert</div><div class="value">{float(perf['realized_pnl']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Ø Trade P/L</div><div class="value">{float(perf['avg_trade_pnl']):,.2f} EUR</div></div>
      </div>
    </div>

    <div class="card">
      <h2>Mini-System / Depot-State</h2>
      <p class="muted">Diese Werte kommen aus dem persistierten Zustandsfile des Mini-Systems.</p>
      <div class="grid">
        <div class="kpi"><div class="label">Cash</div><div class="value">{float(state['cash_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Investiert</div><div class="value">{float(state['total_invested_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Equity</div><div class="value">{float(state['last_equity_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Peak Equity</div><div class="value">{float(state['peak_equity_eur']):,.2f} EUR</div></div>
        <div class="kpi"><div class="label">Drawdown</div><div class="value">{float(state['drawdown_pct']):.2f}%</div></div>
        <div class="kpi"><div class="label">Offene Positionen</div><div class="value">{int(state_positions_count)}</div></div>
      </div>
      <p class="muted">State-Update: {_html_escape(state_updated_at)}</p>
    </div>

    <div class="card">
      <h2>Risikoprofil</h2>
      <p>Max Position: {float(risk.get('max_position_pct', 0.0)) * 100:.0f}% | Stop-Loss: {float(risk.get('stop_loss_pct', 0.0)) * 100:.0f}% | Trailing Stop: {float(risk.get('trailing_stop_pct', 0.0)) * 100:.0f}% | Max Drawdown: {float(risk.get('max_drawdown_pct', 0.0)) * 100:.0f}%</p>
    </div>

    <div class="card">
      <h2>Aktuelle Analyse-Ergebnisse</h2>
      <p class="muted">Backtest- und Signalsicht des aktuellen Laufs.</p>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Name</th>
            <th>Signal</th>
            <th>P/L EUR</th>
            <th>Trades</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          {''.join(current_result_rows)}
        </tbody>
      </table>
      {result_explanations_html}
    </div>

    <div class="card">
      <h2>Aktuelle Kaufkandidaten</h2>
      <p class="muted">Vorauswahl aus dem aktuellen Lauf vor der eigentlichen Handelsplanung.</p>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Name</th>
            <th>Signal</th>
            <th>Score</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {''.join(candidate_rows)}
        </tbody>
      </table>
      {candidate_explanations_html}
    </div>

    <div class="card">
      <h2>{_html_escape(plan_title)}</h2>
      <p class="muted">Dieser Abschnitt zeigt bevorzugt den aktuellen Trading-Plan; ohne frischen Lauf faellt er auf historische Portfolio-Gewichtung zurueck.</p>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Name</th>
            <th>Gewicht</th>
            <th>Kapital</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {''.join(plan_rows)}
        </tbody>
      </table>
      {plan_explanations_html}
    </div>

    <div class="card">
      <h2>Aktuelle Orders</h2>
      <p class="muted">Ein- und Ausstiege aus dem aktuellen Lauf mit ihrer fachlichen Begründung.</p>
      <table>
        <thead>
          <tr>
            <th>Aktion</th>
            <th>Symbol</th>
            <th>Auslöser</th>
            <th>Kapital</th>
            <th>Gewicht</th>
            <th>Learned</th>
          </tr>
        </thead>
        <tbody>
          {''.join(order_rows)}
        </tbody>
      </table>
      {order_explanations_html}
    </div>

    <div class="card">
      <h2>Simuliertes Depot (aktueller Lauf)</h2>
      <p class="muted">Virtuelles Analyse-Depot aus dem letzten CLI-Lauf, getrennt vom persistierten Mini-System-State.</p>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Name</th>
            <th>Qty</th>
            <th>Kurs EUR</th>
            <th>Wert EUR</th>
          </tr>
        </thead>
        <tbody>
          {''.join(simulated_portfolio_rows)}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Letzte Mini-System-Events</h2>
      <p class="muted">Persistierte Historie des Mini-Systems und nicht der aktuelle Analyse-Lauf.</p>
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


def build_dashboard(
    initial_cash: float = 1000.0,
    analysis_result: dict[str, Any] | None = None,
    trading_plan: list[dict[str, Any]] | None = None,
    decisions: dict[str, Any] | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """
    Baut Dashboard-Daten und schreibt JSON + HTML.
    """
    data = build_dashboard_data(
        initial_cash=initial_cash,
        analysis_result=analysis_result,
        trading_plan=trading_plan,
        decisions=decisions,
        profile_name=profile_name,
    )
    _write_dashboard_json(data)
    _write_dashboard_html(data)
    return data
