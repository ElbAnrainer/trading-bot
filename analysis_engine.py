import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

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
from cache_utils import get_cached_metadata, preload_metadata
from data_loader import (
    latest_rate_to_eur,
    fx_rate_to_eur_at,
    fallback_rate_to_eur,
    load_ticker_metadata,
    fetch_dynamic_universe,
)
from market_data_cache import (
    load_benchmark_cached,
    load_data_batch_cached,
    load_fx_to_eur_data_cached,
)
from score_learning import (
    apply_learning_to_candidates,
    print_learning_summary,
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


PROGRESS_BAR_WIDTH = 30
LIVE_BLOCK_HEIGHT = 10
LIVE_BOX_WIDTH = 100
MAX_ANALYSIS_WORKERS = 8

SCREENING_TTL_SECONDS = 900
BACKTEST_TTL_SECONDS = 900
BENCHMARK_TTL_SECONDS = 900
FX_TTL_SECONDS = 3600
IDENTIFIER_REFRESH_COOLDOWN_SECONDS = 24 * 60 * 60

_LIVE_INITIALIZED = False


def _metadata_needs_identifier_refresh(meta):
    missing_identifier = (str(meta.get("isin", "")).strip() in ("", "-")) or (
        str(meta.get("wkn", "")).strip() in ("", "-")
    )
    if not missing_identifier:
        return False

    fetched_at = str(meta.get("fetched_at", "")).strip()
    if not fetched_at:
        return True

    try:
        parsed = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return True

    age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    return age_seconds >= IDENTIFIER_REFRESH_COOLDOWN_SECONDS


def _refresh_metadata_for_symbol(symbol):
    return get_cached_metadata(
        symbol,
        load_ticker_metadata,
        refresh_predicate=_metadata_needs_identifier_refresh,
    )


def _refresh_item_identifiers(item, metadata_cache):
    symbol = item.get("symbol")
    if not symbol:
        return item

    meta = _refresh_metadata_for_symbol(symbol)
    metadata_cache[symbol] = meta
    item["company_name"] = meta.get("name", item.get("company_name", symbol))
    item["isin"] = meta.get("isin", item.get("isin", "-"))
    item["wkn"] = meta.get("wkn", item.get("wkn", "-"))
    return item


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
        return "." * width, 0.0

    ratio = min(max(current / total, 0.0), 1.0)
    filled = int(round(ratio * width))
    bar = "#" * filled + "." * (width - filled)
    return bar, ratio * 100.0


def _is_live_terminal():
    return sys.stdout.isatty()


def _result_hit_rate(result):
    closed_trades = result.get("closed_trades", [])
    if not closed_trades:
        return 0.0
    wins = sum(1 for trade in closed_trades if float(trade.get("pnl_eur", 0.0)) > 0)
    return (wins / len(closed_trades)) * 100.0


def _compute_hit_rate(results):
    wins = 0
    closed = 0

    for result in results:
        for trade in result.get("closed_trades", []):
            closed += 1
            if float(trade.get("pnl_eur", 0.0)) > 0:
                wins += 1

    if closed == 0:
        return 0.0

    return (wins / closed) * 100.0


def _historical_performance_rank(item):
    """
    Echte Vorauswahl eher nach historischer Simulationsleistung statt nur nach Roh-Score.
    Fallback bleibt der Score, wenn es noch kaum Historie gibt.
    """
    score = float(item.get("score", 0.0))
    learned_bonus = float(item.get("learned_bonus", 0.0))
    confidence = float(item.get("learned_confidence", 0.0))

    if confidence > 0:
        return learned_bonus * 100.0 + confidence * 10.0 + score * 0.05

    return score


def _find_top_symbol(analyzed, results):
    if results:
        best = sorted(
            results,
            key=lambda x: (
                float(x.get("pnl_eur", 0.0)),
                float(x.get("hit_rate_pct", 0.0)),
                int(x.get("trade_count", 0)),
            ),
            reverse=True,
        )[0]
        return f"{best.get('symbol', '-')} | P/L {float(best.get('pnl_eur', 0.0)):.2f}"

    best_symbol = "-"
    best_rank = None
    for item in analyzed:
        rank = _historical_performance_rank(item)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_symbol = item.get("symbol", "-")
    return best_symbol


def _box_top(title):
    inner_width = LIVE_BOX_WIDTH - 2
    title = f" {title} "
    dash_total = max(inner_width - len(title), 0)
    left = dash_total // 2
    right = dash_total - left
    return "+" + ("-" * left) + title + ("-" * right) + "+"


def _box_line(content=""):
    inner_width = LIVE_BOX_WIDTH - 2
    return "|" + _fit_text(content, inner_width).ljust(inner_width) + "|"


def _box_bottom():
    return "+" + ("-" * (LIVE_BOX_WIDTH - 2)) + "+"


def _render_live_lines(
    phase,
    current,
    total,
    symbol,
    name,
    started_at,
    analyzed_count=0,
    selected_count=0,
    results=None,
    top_symbol="-",
):
    if results is None:
        results = []

    bar, pct = _render_progress_bar(current, total)

    elapsed = 0.0
    eta = "-"
    if started_at is not None and current > 0 and total > 0:
        elapsed = time.perf_counter() - started_at
        avg = elapsed / current
        remaining = avg * (total - current)
        eta = _format_eta(remaining)

    symbol_text = symbol or "-"
    name_text = name or "-"
    hit_rate = _compute_hit_rate(results)
    total_pnl = sum(float(r.get("pnl_eur", 0.0)) for r in results)
    backtests_done = len(results)

    return [
        _box_top("LIVE PAPER-TRADING TERMINAL"),
        _box_line(f"Phase        : {phase}"),
        _box_line(
            f"Fortschritt  : {current}/{total} | {pct:6.2f}% | ETA: {eta} | Laufzeit: {_format_eta(elapsed)}"
        ),
        _box_line(f"Progress-Bar : [{bar}]"),
        _box_line(f"Symbol       : {symbol_text} | Firma: {_fit_text(name_text, 60)}"),
        _box_line(
            f"Analyse      : Kandidaten: {analyzed_count} | Auswahl: {selected_count} | Backtests: {backtests_done}"
        ),
        _box_line(
            f"Statistik    : Trefferquote: {hit_rate:6.2f}% | Sim-P/L: {total_pnl:10.2f} EUR"
        ),
        _box_line(f"Top-Symbol   : {top_symbol}"),
        _box_line("Hinweis      : Keine echten Orders. Keine Broker-Anbindung. Nur Analyse / Backtesting."),
        _box_bottom(),
    ]


def _init_live_terminal():
    global _LIVE_INITIALIZED

    if not _is_live_terminal() or _LIVE_INITIALIZED:
        return

    sys.stdout.write("\033[?25l")
    sys.stdout.write("\n" * LIVE_BLOCK_HEIGHT)
    sys.stdout.write(f"\033[{LIVE_BLOCK_HEIGHT}A")
    sys.stdout.write("\033[s")
    sys.stdout.flush()
    _LIVE_INITIALIZED = True


def _restore_live_home():
    if _is_live_terminal() and _LIVE_INITIALIZED:
        sys.stdout.write("\033[u")
        sys.stdout.flush()


def _draw_live_block(lines):
    if not _is_live_terminal():
        return

    _init_live_terminal()
    _restore_live_home()

    for line in lines:
        sys.stdout.write("\r\033[2K" + line + "\n")

    _restore_live_home()
    sys.stdout.flush()


def update_live_terminal(
    phase,
    current,
    total,
    symbol="",
    name="",
    started_at=None,
    analyzed_count=0,
    selected_count=0,
    results=None,
    top_symbol="-",
    show_progress=True,
):
    if not show_progress:
        return

    if results is None:
        results = []

    if _is_live_terminal():
        lines = _render_live_lines(
            phase=phase,
            current=current,
            total=total,
            symbol=symbol,
            name=name,
            started_at=started_at,
            analyzed_count=analyzed_count,
            selected_count=selected_count,
            results=results,
            top_symbol=top_symbol,
        )
        _draw_live_block(lines)
        return

    bar, pct = _render_progress_bar(current, total)
    msg = (
        f"[{bar}] {pct:6.2f}% | {phase:<10} | {current:>3}/{total:<3} | "
        f"{symbol} ({_fit_text(name, 28)})"
    )
    sys.stdout.write("\r" + msg.ljust(140))
    sys.stdout.flush()


def finish_live_terminal(show_progress=True):
    global _LIVE_INITIALIZED

    if not show_progress:
        return

    if _is_live_terminal() and _LIVE_INITIALIZED:
        _restore_live_home()
        sys.stdout.write(f"\033[{LIVE_BLOCK_HEIGHT}B")
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        _LIVE_INITIALIZED = False
        return

    sys.stdout.write("\r" + (" " * 140) + "\r")
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

    trade_count = len(summary["closed_trades"])
    hit_rate_pct = _result_hit_rate({"closed_trades": summary["closed_trades"]})

    return {
        "native_currency": native_currency,
        "pnl_eur": pnl_eur,
        "pnl_native": pnl_native,
        "pnl_pct_eur": pnl_pct_eur,
        "trade_count": trade_count,
        "hit_rate_pct": hit_rate_pct,
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
    # Ranking jetzt nach historischer Performance, nicht nur nach Roh-Score
    future = sorted(
        analyzed,
        key=lambda x: (
            _historical_performance_rank(x),
            float(x.get("score", 0.0)),
        ),
        reverse=True,
    )
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
        item["isin"] = meta.get("isin", "-")
        item["wkn"] = meta.get("wkn", "-")
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


def _choose_screening_period(period):
    mapping = {
        "1d": "1d",
        "5d": "5d",
        "1wk": "5d",
        "1mo": "1mo",
        "3mo": "1mo",
        "6mo": "3mo",
        "1y": "3mo",
        "2y": "6mo",
        "3y": "6mo",
    }
    return mapping.get(period, "3mo")


def _analyze_one_symbol(symbol, df, benchmark_df, metadata_cache, min_volume):
    meta = metadata_cache.get(symbol, {})
    fundamentals = meta.get("fundamentals", {})

    info = analyze_symbol(
        df=df,
        symbol=symbol,
        benchmark_df=benchmark_df,
        fundamentals=fundamentals,
    )
    if not info:
        return None

    info["company_name"] = meta.get("name", symbol)
    info["isin"] = meta.get("isin", "-")
    info["wkn"] = meta.get("wkn", "-")

    if info.get("avg_volume", 0) < min_volume:
        return None

    return info


def run_analysis(
    period,
    top_n=DEFAULT_TOP_N,
    min_volume=DEFAULT_MIN_VOLUME,
    long_mode=False,
    show_progress=True,
):
    interval = choose_interval(period)

    print_simulation_notice()

    all_symbols = fetch_dynamic_universe()
    screening_period = _choose_screening_period(period)

    metadata_cache = preload_metadata(all_symbols, load_ticker_metadata)

    screening_batch_data = load_data_batch_cached(
        all_symbols,
        screening_period,
        interval,
        ttl_seconds=SCREENING_TTL_SECONDS,
        max_workers=MAX_ANALYSIS_WORKERS,
    )
    screening_benchmark_df = load_benchmark_cached(
        BENCHMARK_SYMBOL,
        screening_period,
        interval,
        ttl_seconds=BENCHMARK_TTL_SECONDS,
    )

    analyzed = []
    diagnostics_to_print = []

    screening_started_at = time.perf_counter()
    screening_total = len(screening_batch_data)

    futures = []
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_ANALYSIS_WORKERS) as executor:
        for symbol, df in screening_batch_data.items():
            futures.append(
                executor.submit(
                    _analyze_one_symbol,
                    symbol,
                    df,
                    screening_benchmark_df,
                    metadata_cache,
                    min_volume,
                )
            )

        for future in as_completed(futures):
            completed += 1
            info = future.result()
            if info:
                analyzed.append(info)
                if long_mode:
                    diagnostics_to_print.append(info)

                current_symbol = info.get("symbol", "-")
                current_name = info.get("company_name", "-")
            else:
                current_symbol = "-"
                current_name = "-"

            update_live_terminal(
                phase="Analyse",
                current=completed,
                total=screening_total,
                symbol=current_symbol,
                name=current_name,
                started_at=screening_started_at,
                analyzed_count=len(analyzed),
                selected_count=0,
                results=[],
                top_symbol=_find_top_symbol(analyzed, []),
                show_progress=show_progress,
            )

    analyzed = apply_learning_to_candidates(analyzed, min_trades=3)

    future_candidates = build_future_candidates(analyzed, RECOMMENDATION_TOP_N)
    future_candidates = _enrich_with_company_names(future_candidates, metadata_cache)
    future_candidates = [_refresh_item_identifiers(item, metadata_cache) for item in future_candidates]
    diagnostics_to_print = [_refresh_item_identifiers(item, metadata_cache) for item in diagnostics_to_print]

    screened = [x for x in analyzed if x["is_candidate"]]
    screened.sort(
        key=lambda x: (
            _historical_performance_rank(x),
            float(x.get("score", 0.0)),
        ),
        reverse=True,
    )
    analyzed_by_symbol = {item["symbol"]: item for item in analyzed}

    fallback_used = False
    if not screened:
        fallback_used = True
        screened = sorted(
            analyzed,
            key=lambda x: (
                _historical_performance_rank(x),
                float(x.get("score", 0.0)),
            ),
            reverse=True,
        )

    selected_symbols = [x["symbol"] for x in screened[:top_n]]

    results = []
    portfolio = {}
    fx_cache = {}

    if selected_symbols:
        backtest_batch_data = load_data_batch_cached(
            selected_symbols,
            period,
            interval,
            ttl_seconds=BACKTEST_TTL_SECONDS,
            max_workers=MAX_ANALYSIS_WORKERS,
        )

        backtest_started_at = time.perf_counter()
        backtest_total = len(selected_symbols)

        for idx, symbol in enumerate(selected_symbols, 1):
            df = backtest_batch_data.get(symbol)
            if df is None or df.empty:
                continue

            meta = metadata_cache.get(symbol) or _refresh_metadata_for_symbol(symbol)
            if _metadata_needs_identifier_refresh(meta):
                meta = _refresh_metadata_for_symbol(symbol)
            metadata_cache[symbol] = meta
            native_currency = meta.get("currency", "USD")

            update_live_terminal(
                phase="Backtest",
                current=idx,
                total=backtest_total,
                symbol=symbol,
                name=meta.get("name", ""),
                started_at=backtest_started_at,
                analyzed_count=len(analyzed),
                selected_count=len(selected_symbols),
                results=results,
                top_symbol=_find_top_symbol(analyzed, results),
                show_progress=show_progress,
            )

            if native_currency not in fx_cache:
                fx_df = load_fx_to_eur_data_cached(
                    native_currency,
                    period,
                    interval,
                    ttl_seconds=FX_TTL_SECONDS,
                )
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

            result["symbol"] = symbol
            result["company_name"] = meta.get("name", symbol)
            result["isin"] = meta.get("isin", "-")
            result["wkn"] = meta.get("wkn", "-")
            result["signal"] = signal or "HOLD"
            result["signal_price_eur"] = price_eur
            result["signal_price_native"] = price_native

            analyzed_match = analyzed_by_symbol.get(symbol)
            if analyzed_match:
                result["score"] = analyzed_match.get("score", 0.0)
                result["reasons"] = analyzed_match.get("reasons", [])
                result["score_before_learning"] = analyzed_match.get("score_before_learning", result["score"])
                result["learned_bonus"] = analyzed_match.get("learned_bonus", 0.0)
                result["learned_confidence"] = analyzed_match.get("learned_confidence", 0.0)

            if signal and price_eur is not None and price_native is not None:
                log_trade_decision(
                    symbol=symbol,
                    company=meta.get("name", symbol),
                    isin=result.get("isin", "-"),
                    wkn=result.get("wkn", "-"),
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
                    isin=result.get("isin", "-"),
                    wkn=result.get("wkn", "-"),
                    signal="SELL",
                    price_eur=price_eur if price_eur is not None else 0.0,
                    score=trade_info["score"],
                    reason=trade_info["reason"],
                    closed_trade=trade_info["closed_trade"],
                    realized_pnl_eur=trade_info["realized_pnl_eur"],
                )

            if signal == "BUY" and price_eur is not None and price_native is not None:
                portfolio[symbol] = {
                    "qty": 10,
                    "price_eur": price_eur,
                    "price_native": price_native,
                    "native_currency": native_currency,
                    "company_name": meta.get("name", symbol),
                    "isin": meta.get("isin", "-"),
                    "wkn": meta.get("wkn", "-"),
                }
            elif signal == "SELL" and symbol in portfolio:
                del portfolio[symbol]

            results.append(result)

    finish_live_terminal(show_progress=show_progress)

    if fallback_used and analyzed:
        print("\nHinweis: Keine Aktie hat alle Filter erfüllt.")
        print("Es werden deshalb die historisch/performance-basiert besten verfügbaren Aktien als Fallback genutzt.\n")

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
            future_candidates=future_candidates,
        )
        print_learning_summary()
        print_performance()
        dashboard_result = {
            "period": period,
            "interval": interval,
            "results": [],
            "portfolio": {},
            "future_candidates": future_candidates,
        }
        build_dashboard(analysis_result=dashboard_result)
        return dashboard_result

    if long_mode:
        for info in diagnostics_to_print:
            print_diagnostics(info)

    if long_mode:
        print_future_candidates(future_candidates)
    else:
        print_future_candidates_compact(future_candidates)

    print_buy_blockers_summary(collect_buy_blockers(analyzed))

    for result in results:
        signal = result.get("signal")
        price_eur = result.get("signal_price_eur")
        price_native = result.get("signal_price_native")
        native_currency = result["native_currency"]

        if signal and price_eur is not None and price_native is not None:
            print_recommendation(
                result["symbol"],
                signal,
                price_eur,
                price_native,
                native_currency,
                isin=result.get("isin", "-"),
                wkn=result.get("wkn", "-"),
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
                result["symbol"],
                result["company_name"],
                result["isin"],
                result["wkn"],
                result["closed_trades"],
                result["native_currency"],
            )
            print_equity_curve_terminal(
                result["symbol"],
                result["equity_curve"],
                isin=result.get("isin", "-"),
                wkn=result.get("wkn", "-"),
            )

    # ECHTES PERFORMANCE-RANKING
    results.sort(
        key=lambda x: (
            float(x.get("pnl_eur", 0.0)),
            float(x.get("hit_rate_pct", 0.0)),
            int(x.get("trade_count", 0)),
        ),
        reverse=True,
    )

    print_ranking(results)
    print_portfolio(portfolio)
    print_buy_overview(future_candidates)

    save_run_outputs(
        output_dir=REPORTS_DIR,
        period=period,
        interval=interval,
        results=results,
        portfolio=portfolio,
        future_candidates=future_candidates,
    )

    print_learning_summary()
    print_performance()
    dashboard_result = {
        "period": period,
        "interval": interval,
        "results": results,
        "portfolio": portfolio,
        "future_candidates": future_candidates,
    }
    build_dashboard(analysis_result=dashboard_result)

    return dashboard_result
