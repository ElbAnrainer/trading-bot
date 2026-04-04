import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path


def _ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def _json_safe_results(results):
    safe = []
    for item in results:
        safe.append(
            {
                "symbol": item.get("symbol"),
                "company_name": item.get("company_name"),
                "isin": item.get("isin"),
                "wkn": item.get("wkn"),
                "signal": item.get("signal"),
                "native_currency": item.get("native_currency"),
                "pnl_eur": item.get("pnl_eur"),
                "pnl_native": item.get("pnl_native"),
                "pnl_pct_eur": item.get("pnl_pct_eur"),
                "trade_count": item.get("trade_count"),
                "hit_rate_pct": item.get("hit_rate_pct"),
                "score": item.get("score"),
                "last_price_eur": item.get("last_price_eur"),
                "last_price_native": item.get("last_price_native"),
                "initial_cash_eur": item.get("initial_cash_eur"),
                "current_equity_eur": item.get("current_equity_eur"),
            }
        )
    return safe


def _json_safe_candidates(candidates):
    safe = []
    for item in candidates or []:
        safe.append(
            {
                "symbol": item.get("symbol"),
                "company_name": item.get("company_name", item.get("company")),
                "isin": item.get("isin"),
                "wkn": item.get("wkn"),
                "future_signal": item.get("future_signal"),
                "score": item.get("score"),
                "score_before_learning": item.get("score_before_learning"),
                "learned_bonus": item.get("learned_bonus"),
                "learned_confidence": item.get("learned_confidence"),
            }
        )
    return safe


def _json_safe_trading_plan(plan):
    safe = []
    for item in plan or []:
        safe.append(
            {
                "symbol": item.get("symbol"),
                "company": item.get("company", item.get("company_name")),
                "isin": item.get("isin"),
                "wkn": item.get("wkn"),
                "weight": item.get("weight"),
                "capital": item.get("capital"),
                "learned_score": item.get("learned_score"),
            }
        )
    return safe


def _json_safe_decisions(decisions):
    if not decisions:
        return {}

    safe_orders = []
    for order in decisions.get("orders", []):
        safe_orders.append(
            {
                "action": order.get("action"),
                "symbol": order.get("symbol"),
                "reason": order.get("reason"),
                "capital": order.get("capital"),
                "weight": order.get("weight"),
                "learned_score": order.get("learned_score"),
            }
        )

    return {
        "orders": safe_orders,
        "drawdown_state": decisions.get("drawdown_state", {}),
        "risk": decisions.get("risk", {}),
    }


def write_latest_json(
    output_dir,
    period,
    interval,
    results,
    portfolio,
    profile_name=None,
    future_candidates=None,
    trading_plan=None,
    decisions=None,
):
    _ensure_dir(output_dir)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "period": period,
        "interval": interval,
        "profile_name": profile_name,
        "results": _json_safe_results(results),
        "portfolio": portfolio,
        "future_candidates": _json_safe_candidates(future_candidates),
        "trading_plan": _json_safe_trading_plan(trading_plan),
        "decisions": _json_safe_decisions(decisions),
    }

    target = Path(output_dir) / "latest_run.json"
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def update_latest_json_context(
    output_dir,
    *,
    profile_name=None,
    future_candidates=None,
    trading_plan=None,
    decisions=None,
):
    _ensure_dir(output_dir)

    target = Path(output_dir) / "latest_run.json"
    if target.exists():
        with open(target, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = {}

    if profile_name is not None:
        payload["profile_name"] = profile_name
    if future_candidates is not None:
        payload["future_candidates"] = _json_safe_candidates(future_candidates)
    if trading_plan is not None:
        payload["trading_plan"] = _json_safe_trading_plan(trading_plan)
    if decisions is not None:
        payload["decisions"] = _json_safe_decisions(decisions)

    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def append_history_csv(output_dir, period, interval, results):
    _ensure_dir(output_dir)

    target = Path(output_dir) / "history.csv"
    file_exists = target.exists()

    with open(target, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(
                [
                    "generated_at_utc",
                    "period",
                    "interval",
                    "symbol",
                    "company_name",
                    "signal",
                    "native_currency",
                    "pnl_eur",
                    "pnl_native",
                    "pnl_pct_eur",
                    "trade_count",
                    "last_price_eur",
                    "last_price_native",
                ]
            )

        now_str = datetime.now(timezone.utc).isoformat()

        for item in results:
            writer.writerow(
                [
                    now_str,
                    period,
                    interval,
                    item.get("symbol"),
                    item.get("company_name"),
                    item.get("signal"),
                    item.get("native_currency"),
                    item.get("pnl_eur"),
                    item.get("pnl_native"),
                    item.get("pnl_pct_eur"),
                    item.get("trade_count"),
                    item.get("last_price_eur"),
                    item.get("last_price_native"),
                ]
            )


def render_dashboard_html(output_dir, period, interval, results, portfolio):
    _ensure_dir(output_dir)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    rows = []
    for item in results:
        symbol = html.escape(str(item.get("symbol", "")))
        isin = html.escape(str(item.get("isin", "-")))
        wkn = html.escape(str(item.get("wkn", "-")))
        name = html.escape(str(item.get("company_name", "")))
        signal = html.escape(str(item.get("signal", "")))
        native_currency = html.escape(str(item.get("native_currency", "")))
        pnl_eur = float(item.get("pnl_eur", 0.0))
        pnl_native = float(item.get("pnl_native", 0.0))
        pnl_pct_eur = float(item.get("pnl_pct_eur", 0.0))
        trade_count = int(item.get("trade_count", 0))

        css_class = "pos" if pnl_eur > 0 else "neg" if pnl_eur < 0 else "neu"

        rows.append(
            f"""
            <tr>
              <td>{symbol}</td>
              <td>{isin}</td>
              <td>{wkn}</td>
              <td>{name}</td>
              <td>{signal}</td>
              <td>{native_currency}</td>
              <td class="{css_class}">{pnl_eur:.2f} EUR</td>
              <td>{pnl_native:.2f} {native_currency}</td>
              <td>{pnl_pct_eur:.2f}%</td>
              <td>{trade_count}</td>
            </tr>
            """
        )

    portfolio_rows = []
    for symbol, pos in portfolio.items():
        isin = html.escape(str(pos.get("isin", "-")))
        wkn = html.escape(str(pos.get("wkn", "-")))
        qty = pos.get("qty", 0)
        price_eur = float(pos.get("price_eur", 0.0))
        price_native = float(pos.get("price_native", 0.0))
        native_currency = html.escape(str(pos.get("native_currency", "")))
        value_eur = qty * price_eur

        portfolio_rows.append(
            f"""
            <tr>
              <td>{html.escape(symbol)}</td>
              <td>{isin}</td>
              <td>{wkn}</td>
              <td>{qty}</td>
              <td>{price_eur:.2f} EUR</td>
              <td>{price_native:.2f} {native_currency}</td>
              <td>{value_eur:.2f} EUR</td>
            </tr>
            """
        )

    if not portfolio_rows:
        portfolio_rows.append(
            """
            <tr>
              <td colspan="7">Keine Positionen im virtuellen Depot.</td>
            </tr>
            """
        )

    html_doc = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Trading Bot Dashboard</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 24px;
      background: #f7f7f7;
      color: #222;
    }}
    h1, h2 {{
      margin-bottom: 8px;
    }}
    .meta {{
      margin-bottom: 20px;
      color: #555;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      background: white;
      margin-bottom: 24px;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 8px 10px;
      text-align: left;
    }}
    th {{
      background: #f0f0f0;
    }}
    .pos {{
      color: #0a8a28;
      font-weight: bold;
    }}
    .neg {{
      color: #b30000;
      font-weight: bold;
    }}
    .neu {{
      color: #444;
    }}
  </style>
</head>
<body>
  <h1>Trading Bot Dashboard</h1>
  <div class="meta">
    Generiert: {generated_at}<br>
    Zeitraum: {html.escape(period)}<br>
    Intervall: {html.escape(interval)}
  </div>

  <h2>Ranking</h2>
  <table>
    <thead>
      <tr>
        <th>Symbol</th>
        <th>ISIN</th>
        <th>WKN</th>
        <th>Name</th>
        <th>Signal</th>
        <th>Währung</th>
        <th>P/L EUR</th>
        <th>P/L nativ</th>
        <th>P/L %</th>
        <th>Trades</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows) if rows else '<tr><td colspan="10">Keine Ergebnisse.</td></tr>'}
    </tbody>
  </table>

  <h2>Virtuelles Depot</h2>
  <table>
    <thead>
      <tr>
        <th>Symbol</th>
        <th>ISIN</th>
        <th>WKN</th>
        <th>Stück</th>
        <th>Kurs EUR</th>
        <th>Kurs nativ</th>
        <th>Wert EUR</th>
      </tr>
    </thead>
    <tbody>
      {''.join(portfolio_rows)}
    </tbody>
  </table>
</body>
</html>
"""

    target = Path(output_dir) / "dashboard.html"
    with open(target, "w", encoding="utf-8") as f:
        f.write(html_doc)


def save_run_outputs(
    output_dir,
    period,
    interval,
    results,
    portfolio,
    profile_name=None,
    future_candidates=None,
    trading_plan=None,
    decisions=None,
):
    write_latest_json(
        output_dir,
        period,
        interval,
        results,
        portfolio,
        profile_name=profile_name,
        future_candidates=future_candidates,
        trading_plan=trading_plan,
        decisions=decisions,
    )
    append_history_csv(output_dir, period, interval, results)
    render_dashboard_html(output_dir, period, interval, results, portfolio)
