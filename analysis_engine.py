from cli import choose_interval
from config import (
    BENCHMARK_SYMBOL,
    COOLDOWN_BARS,
    INITIAL_CASH_EUR,
    RECOMMENDATION_TOP_N,
    REPORTS_DIR,
)
from broker import Broker
from data_loader import (
    fallback_rate_to_eur,
    fetch_dynamic_universe,
    fx_rate_to_eur_at,
    latest_rate_to_eur,
    load_data,
    load_data_batch,
    load_fx_to_eur_data,
    load_ticker_metadata,
)
from output import (
    print_buy_blockers_summary,
    print_buy_overview,
    print_closed_trades,
    print_diagnostics,
    print_equity_curve_terminal,
    print_financial_overview,
    print_future_candidates,
    print_portfolio,
    print_ranking,
    print_recommendation,
    print_summary_only,
)
from report_writer import save_run_outputs
from strategy import (
    add_signals,
    analyze_symbol,
    compute_qty,
    normalize_signal_from_row,
    stop_loss_price,
    take_profit_price,
)


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
        equity_curve.append({"time": ts, "equity_eur": summary_now["equity_eur"]})

    last_price_native = float(df.iloc[-1]["Close"])
    summary = broker.summary(last_price_native, rate_to_eur_latest)
    current_equity_eur = summary["equity_eur"]
    pnl_eur = current_equity_eur - INITIAL_CASH_EUR
    pnl_pct_eur = (pnl_eur / INITIAL_CASH_EUR * 100) if INITIAL_CASH_EUR else 0.0
    pnl_native = pnl_eur / rate_to_eur_latest if rate_to_eur_latest > 0 else 0.0

    return {
        "native_currency": native_currency,
        "pnl_eur": pnl_eur,
        "pnl_native": pnl_native,
        "pnl_pct_eur": pnl_pct_eur,
        "trade_count": len(summary["closed_trades"]),
        "closed_trades": summary["closed_trades"],
        "last_price_native": last_price_native,
        "last_price_eur": last_price_native * rate_to_eur_latest,
        "initial_cash_eur": INITIAL_CASH_EUR,
        "current_equity_eur": current_equity_eur,
        "equity_curve": equity_curve,
    }


def build_future_candidates(analyzed, top_n):
    return sorted(analyzed, key=lambda x: x["score"], reverse=True)[:top_n]


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


def run_analysis(period, top_n, min_volume, long_mode):
    interval = choose_interval(period)
    all_symbols = fetch_dynamic_universe()
    batch_data = load_data_batch(all_symbols, period, interval, chunk_size=25, pause_seconds=0.2)
    benchmark_df = load_data(BENCHMARK_SYMBOL, period, interval)

    analyzed = []
    for symbol, df in batch_data.items():
        info = analyze_symbol(df=df, symbol=symbol, benchmark_df=benchmark_df, fundamentals={})
        if info:
            if long_mode:
                print_diagnostics(info)
            if info["avg_volume"] >= min_volume:
                analyzed.append(info)

    future_candidates = build_future_candidates(analyzed, RECOMMENDATION_TOP_N)
    print_future_candidates(future_candidates)
    print_buy_blockers_summary(collect_buy_blockers(analyzed))

    screened = sorted([x for x in analyzed if x["is_candidate"]], key=lambda x: x["score"], reverse=True)
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
        save_run_outputs(output_dir=REPORTS_DIR, period=period, interval=interval, results=[], portfolio={})
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
    metadata_cache = {}

    for symbol in selected_symbols:
        df = batch_data.get(symbol)
        if df is None or df.empty:
            continue

        if symbol not in metadata_cache:
            metadata_cache[symbol] = load_ticker_metadata(symbol)
        meta = metadata_cache[symbol]
        native_currency = meta.get("currency", "USD")

        if native_currency not in fx_cache:
            fx_df = load_fx_to_eur_data(native_currency, period, interval)
            fx_cache[native_currency] = {
                "df": fx_df,
                "latest": latest_rate_to_eur(fx_df, fallback_rate_to_eur(native_currency)),
            }

        fx_df = fx_cache[native_currency]["df"]
        rate_to_eur_latest = fx_cache[native_currency]["latest"]
        signal, price_eur, price_native = get_signal_from_df(df, rate_to_eur_latest)

        if signal and price_eur is not None and price_native is not None:
            print_recommendation(symbol, signal, price_eur, price_native, native_currency)

        result = backtest_from_df(df, native_currency, fx_df, rate_to_eur_latest)
        if not result:
            continue

        result.update({
            "symbol": symbol,
            "company_name": meta.get("name", symbol),
            "isin": meta.get("isin", "-"),
            "wkn": meta.get("wkn", "-"),
            "signal": signal or "HOLD",
        })

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
            }
        elif signal == "SELL" and symbol in portfolio:
            del portfolio[symbol]

        results.append(result)

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

    return {
        "period": period,
        "interval": interval,
        "results": results,
        "portfolio": portfolio,
        "future_candidates": future_candidates,
    }
