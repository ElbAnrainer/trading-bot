import sys
import time

from config import (
    INITIAL_CASH_EUR,
    DEFAULT_TOP_N,
    DEFAULT_MIN_VOLUME,
    COOLDOWN_BARS,
    REPORTS_DIR,
    RECOMMENDATION_TOP_N,
    BENCHMARK_SYMBOL,
)
from broker import Broker
from data_loader import (
    load_data,
    load_data_batch,
    load_fx_to_eur_data,
    latest_rate_to_eur,
    fx_rate_to_eur_at,
    fallback_rate_to_eur,
    load_ticker_metadata,
    fetch_dynamic_universe,
)
from strategy import (
    add_signals,
    compute_qty,
    normalize_signal_from_row,
    analyze_symbol,
    stop_loss_price,
    take_profit_price,
)
from output import (
    print_summary_only,
    print_ranking,
    print_closed_trades,
    print_recommendation,
    print_portfolio,
    print_financial_overview,
    print_equity_curve_terminal,
    print_future_candidates,
    print_future_candidates_compact,
    print_diagnostics,
    print_buy_overview,
    print_buy_blockers_summary,
    print_simulation_notice,
)
from report_writer import save_run_outputs
from cli import choose_interval
from journal import log_trade_decision
from performance import print_performance
from dashboard import build_dashboard


PROGRESS_BAR_WIDTH = 24
PROGRESS_LINE_WIDTH = 140


def _fit_text(text, width):
    text = str(text or "")
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def _format_eta(seconds):
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours}h {minutes:02d}m {sec:02d}s"
    if minutes > 0:
        return f"{minutes}m {sec:02d}s"
    return f"{sec}s"


def _render_progress_bar(current, total, width=PROGRESS_BAR_WIDTH):
    if total <= 0:
        return "░" * width, 0.0

    ratio = min(max(current / total, 0.0), 1.0)
    filled = int(round(ratio * width))
    bar = "█" * filled + "░" * (width - filled)
    return bar, ratio * 100


def print_progress(current, total, phase, symbol="", name="", started_at=None):
    bar, pct = _render_progress_bar(current, total)

    eta = ""
    if started_at is not None and current > 0 and total > 0:
        elapsed = time.perf_counter() - started_at
        avg = elapsed / current
        remaining = avg * (total - current)
        eta = f" | ETA: {_format_eta(remaining)}"

    symbol_part = symbol or "-"
    name_part = f" ({_fit_text(name, 28)})" if name else ""

    msg = (
        f"[{bar}] "
        f"{pct:6.2f}% | "
        f"{phase:<10} | "
        f"{current:>3}/{total:<3} | "
        f"{symbol_part}{name_part}"
        f"{eta}"
    )

    sys.stdout.write("\r" + msg.ljust(PROGRESS_LINE_WIDTH))
    sys.stdout.flush()


def clear_progress_line():
    sys.stdout.write("\r" + (" " * PROGRESS_LINE_WIDTH) + "\r")
    sys.stdout.flush()


def get_signal_from_df(df, rate_to_eur_latest):
    df = add_signals(df)

    if df.empty:
        return None, None, None

    last = df.iloc[-1]
    signal = normalize_signal_from_row(last)
    price_native = float(last["Close"])
    price_eur = price_native * rate_to_eur_latest

    return signal, price_eur, price_native


def backtest_from_df(df, native_currency, fx_df, rate_to_eur_latest):
    df = add_signals(df).dropna()

    if df.empty:
        return None

    broker = Broker(INITIAL_CASH_EUR)
    equity_curve = []
    cooldown = 0

    for i, row in df.iterrows():
        price_native = float(row["Close"])
        ts = str(i)
        rate_to_eur = fx_rate_to_eur_at(ts, fx_df, rate_to_eur_latest)

        if broker.position > 0 and broker.open_trade is not None:
            entry = broker.open_trade["buy_price_native"]
            sl = stop_loss_price(entry)
            tp = take_profit_price(entry)

            if price_native <= sl:
                broker.sell(price_native, ts, rate_to_eur, reason="STOP_LOSS")
                cooldown = COOLDOWN_BARS
            elif price_native >= tp:
                broker.sell(price_native, ts, rate_to_eur, reason="TAKE_PROFIT")
                cooldown = COOLDOWN_BARS
            elif bool(row["sell_signal"]):
                broker.sell(price_native, ts, rate_to_eur, reason="SIGNAL")
                cooldown = COOLDOWN_BARS

        if broker.position == 0:
            if cooldown > 0:
                cooldown -= 1
            elif bool(row["buy_signal"]):
                qty = compute_qty(broker.cash_eur, price_native * rate_to_eur)
                if qty > 0:
                    broker.buy(price_native, qty, ts, rate_to_eur, native_currency)

        summary_now = broker.summary(price_native, rate_to_eur)
        equity_curve.append(
            {
                "time": ts,
                "equity_eur": summary_now["equity_eur"],
            }
        )

    last_price_native = float(df.iloc[-1]["Close"])
    end_rate = rate_to_eur_latest
    summary = broker.summary(last_price_native, end_rate)

    current_equity_eur = summary["equity_eur"]
    pnl_eur = current_equity_eur - INITIAL_CASH_EUR
    pnl_pct_eur = (pnl_eur / INITIAL_CASH_EUR * 100) if INITIAL_CASH_EUR else 0.0

    pnl_native = 0.0
    if end_rate > 0:
        pnl_native = pnl_eur / end_rate

    return {
        "native_currency": native_currency,
        "pnl_eur": pnl_eur,
        "pnl_native": pnl_native,
        "pnl_pct_eur": pnl_pct_eur,
        "trade_count": len(summary["closed_trades"]),
        "closed_trades": summary["closed_trades"],
        "last_price_native": last_price_native,
        "last_price_eur": last_price_native * end_rate,
        "initial_cash_eur": INITIAL_CASH_EUR,
        "current_equity_eur": current_equity_eur,
        "equity_curve": equity_curve,
        "score": 0.0,
        "reasons": [],
    }


def build_future_candidates(analyzed, top_n):
    future = sorted(analyzed, key=lambda x: x["score"], reverse=True)
    return future[:top_n]


def collect_buy_blockers(analyzed):
    blockers = {
        "Trend fehlt": 0,
        "Breakout fehlt": 0,
        "Momentum fehlt": 0,
        "Volatilität fehlt": 0,
        "Relative Stärke fehlt": 0,
        "Fundamental schwach": 0,
        "Score zu niedrig": 0,
    }

    for item in analyzed:
        if item.get("future_signal") == "BUY":
            continue

        if not item.get("trend_ok", False):
            blockers["Trend fehlt"] += 1
        if not item.get("breakout_ok", False):
            blockers["Breakout fehlt"] += 1
        if not item.get("momentum_ok", False):
            blockers["Momentum fehlt"] += 1
        if not item.get("volatility_ok", False):
            blockers["Volatilität fehlt"] += 1
        if not item.get("relative_strength_ok", False):
            blockers["Relative Stärke fehlt"] += 1
        if item.get("fundamental_score", 0) < 2:
            blockers["Fundamental schwach"] += 1
        if item.get("score", 0) < 40:
            blockers["Score zu niedrig"] += 1

    return blockers


def _enrich_with_company_names(items, metadata_cache):
    for item in items:
        meta = metadata_cache.get(item["symbol"], {})
        item["company_name"] = meta.get("name", item["symbol"])
    return items


def _journal_closed_trades(result):
    trades = result.get("closed_trades", [])
    score = result.get("score", 0.0)
    reasons = ", ".join(result.get("reasons", []))

    for trade in trades:
        realized_pnl_eur = float(trade.get("pnl_eur", 0.0))
        yield {
            "closed_trade": True,
            "realized_pnl_eur": realized_pnl_eur,
            "score": score,
            "reason": reasons,
        }


def run_analysis(
    period,
    top_n=DEFAULT_TOP_N,
    min_volume=DEFAULT_MIN_VOLUME,
    long_mode=False,
):
    interval = choose_interval(period)

    print_simulation_notice()

    all_symbols = fetch_dynamic_universe()
    batch_data = load_data_batch(
        all_symbols,
        period,
        interval,
        chunk_size=25,
        pause_seconds=0.2,
    )
    benchmark_df = load_data(BENCHMARK_SYMBOL, period, interval)

    analyzed = []
    metadata_cache = {}

    screening_started_at = time.perf_counter()
    screening_total = len(batch_data)

    for idx, (symbol, df) in enumerate(batch_data.items(), 1):
        if symbol not in metadata_cache:
            metadata_cache[symbol] = load_ticker_metadata(symbol)

        meta = metadata_cache[symbol]
        fundamentals = meta.get("fundamentals", {})

        print_progress(
            current=idx,
            total=screening_total,
            phase="Analyse",
            symbol=symbol,
            name=meta.get("name", ""),
            started_at=screening_started_at,
        )

        info = analyze_symbol(
            df=df,
            symbol=symbol,
            benchmark_df=benchmark_df,
            fundamentals=fundamentals,
        )

        if info:
            info["company_name"] = meta.get("name", symbol)

            if long_mode:
                clear_progress_line()
                print_diagnostics(info)

            if info["avg_volume"] >= min_volume:
                analyzed.append(info)

    clear_progress_line()

    future_candidates = build_future_candidates(analyzed, RECOMMENDATION_TOP_N)
    future_candidates = _enrich_with_company_names(future_candidates, metadata_cache)

    if long_mode:
        print_future_candidates(future_candidates)
    else:
        print_future_candidates_compact(future_candidates)

    print_buy_blockers_summary(collect_buy_blockers(analyzed))

    screened = [x for x in analyzed if x["is_candidate"]]
    screened.sort(key=lambda x: x["score"], reverse=True)

    fallback_used = False
    if not screened:
        fallback_used = True
        screened = sorted(analyzed, key=lambda x: x["score"], reverse=True)

    selected_symbols = [x["symbol"] for x in screened[:top_n]]

    if fallback_used and analyzed:
        print("\nHinweis: Keine Aktie hat alle Filter erfüllt.")
        print("Es werden deshalb die bestbewerteten verfügbaren Aktien als Fallback genutzt.\n")

    if not selected_symbols:
        print("\nKeine auswertbaren Aktien gefunden.\n")
        print_ranking([])
        print_portfolio({})
        print_buy_overview(future_candidates)
        save_run_outputs(
            output_dir=REPORTS_DIR,
            period=period,
            interval=interval,
            results=[],
            portfolio={},
        )
        print_performance()
        build_dashboard()
        return {
            "period": period,
            "interval": interval,
            "results": [],
            "portfolio": {},
            "future_candidates": future_candidates,
        }

    results = []
    portfolio = {}
    fx_cache = {}

    backtest_started_at = time.perf_counter()
    backtest_total = len(selected_symbols)

    for idx, symbol in enumerate(selected_symbols, 1):
        df = batch_data.get(symbol)
        if df is None or df.empty:
            continue

        if symbol not in metadata_cache:
            metadata_cache[symbol] = load_ticker_metadata(symbol)

        meta = metadata_cache[symbol]
        native_currency = meta.get("currency", "USD")

        print_progress(
            current=idx,
            total=backtest_total,
            phase="Backtest",
            symbol=symbol,
            name=meta.get("name", ""),
            started_at=backtest_started_at,
        )

        if native_currency not in fx_cache:
            fx_df = load_fx_to_eur_data(native_currency, period, interval)
            fx_cache[native_currency] = {
                "df": fx_df,
                "latest": latest_rate_to_eur(
                    fx_df,
                    fallback_rate_to_eur(native_currency),
                ),
            }

        fx_df = fx_cache[native_currency]["df"]
        rate_to_eur_latest = fx_cache[native_currency]["latest"]

        signal, price_eur, price_native = get_signal_from_df(
            df,
            rate_to_eur_latest,
        )

        result = backtest_from_df(
            df,
            native_currency,
            fx_df,
            rate_to_eur_latest,
        )
        if not result:
            continue

        clear_progress_line()

        result["symbol"] = symbol
        result["company_name"] = meta.get("name", symbol)
        result["isin"] = meta.get("isin", "-")
        result["wkn"] = meta.get("wkn", "-")
        result["signal"] = signal or "HOLD"

        analyzed_match = next((x for x in analyzed if x["symbol"] == symbol), None)
        if analyzed_match:
            result["score"] = analyzed_match.get("score", 0.0)
            result["reasons"] = analyzed_match.get("reasons", [])

        if signal and price_eur is not None and price_native is not None:
            print_recommendation(symbol, signal, price_eur, price_native, native_currency)

            log_trade_decision(
                symbol=symbol,
                company=meta.get("name", symbol),
                signal=signal,
                price_eur=price_eur,
                score=result.get("score", 0.0),
                reason=", ".join(result.get("reasons", [])),
                closed_trade=False,
                realized_pnl_eur=0.0,
            )

        for trade_info in _journal_closed_trades(result):
            log_trade_decision(
                symbol=symbol,
                company=meta.get("name", symbol),
                signal="SELL",
                price_eur=price_eur if price_eur is not None else 0.0,
                score=trade_info["score"],
                reason=trade_info["reason"],
                closed_trade=trade_info["closed_trade"],
                realized_pnl_eur=trade_info["realized_pnl_eur"],
            )

        print_financial_overview(
            result["initial_cash_eur"],
            result["current_equity_eur"],
            result["pnl_eur"],
            result["native_currency"],
            result["pnl_native"],
        )
        print_summary_only(result["closed_trades"], result["native_currency"])

        if long_mode:
            print_closed_trades(
                symbol,
                result["company_name"],
                result["isin"],
                result["wkn"],
                result["closed_trades"],
                result["native_currency"],
            )
            print_equity_curve_terminal(symbol, result["equity_curve"])

        if signal == "BUY" and price_eur is not None and price_native is not None:
            portfolio[symbol] = {
                "qty": 10,
                "price_eur": price_eur,
                "price_native": price_native,
                "native_currency": native_currency,
                "company_name": meta.get("name", symbol),
            }
        elif signal == "SELL" and symbol in portfolio:
            del portfolio[symbol]

        results.append(result)

    clear_progress_line()

    results.sort(key=lambda x: x["pnl_eur"], reverse=True)

    print_ranking(results)
    print_portfolio(portfolio)
    print_buy_overview(future_candidates)

    save_run_outputs(
        output_dir=REPORTS_DIR,
        period=period,
        interval=interval,
        results=results,
        portfolio=portfolio,
    )

    print_performance()
    build_dashboard()

    return {
        "period": period,
        "interval": interval,
        "results": results,
        "portfolio": portfolio,
        "future_candidates": future_candidates,
    }
