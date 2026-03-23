from output import (
    print_summary_only,
    print_ranking,
    print_recommendation,
    print_portfolio,
    print_closed_trades,
    print_financial_overview,
    print_equity_curve_terminal,
    print_future_candidates,
)


def test_print_summary_only_outputs_expected_text(capsys):
    closed_trades = [
        {"pnl_eur": 10.5, "pnl_native": 11.2},
        {"pnl_eur": -5.0, "pnl_native": -5.4},
    ]

    print_summary_only(closed_trades, "USD")

    captured = capsys.readouterr()
    assert "GESAMT" in captured.out
    assert "Abgeschlossene Trades" in captured.out
    assert "Gewinntrades" in captured.out
    assert "Verlusttrades" in captured.out


def test_print_ranking_outputs_symbols(capsys):
    results = [
        {
            "symbol": "AAPL",
            "pnl_eur": 120.0,
            "pnl_native": 130.0,
            "native_currency": "USD",
            "pnl_pct_eur": 1.2,
            "trade_count": 5,
        },
        {
            "symbol": "SAP",
            "pnl_eur": -20.0,
            "pnl_native": -20.0,
            "native_currency": "EUR",
            "pnl_pct_eur": -0.2,
            "trade_count": 3,
        },
    ]

    print_ranking(results)

    captured = capsys.readouterr()
    assert "RANKING DER BESTEN BACKTESTS" in captured.out
    assert "AAPL" in captured.out
    assert "SAP" in captured.out


def test_print_future_candidates_outputs_reasons(capsys):
    candidates = [
        {
            "symbol": "AAPL",
            "future_signal": "BUY",
            "strength": "hoch",
            "risk": "mittel",
            "score": 42.5,
            "reasons": ["über SMA200", "Breakout"],
        }
    ]

    print_future_candidates(candidates)

    captured = capsys.readouterr()
    assert "TOP-KANDIDATEN FÜR DIE ZUKUNFT" in captured.out
    assert "AAPL" in captured.out
    assert "Breakout" in captured.out


def test_print_recommendation_outputs_signal(capsys):
    print_recommendation("AAPL", "BUY", 123.45, 134.56, "USD")

    captured = capsys.readouterr()
    assert "AAPL" in captured.out
    assert "BUY" in captured.out


def test_print_portfolio_outputs_positions(capsys):
    portfolio = {
        "AAPL": {"qty": 10, "price_eur": 100.0, "price_native": 110.0, "native_currency": "USD"},
        "SAP": {"qty": 5, "price_eur": 200.0, "price_native": 200.0, "native_currency": "EUR"},
    }

    print_portfolio(portfolio)

    captured = capsys.readouterr()
    assert "DEPOT" in captured.out
    assert "AAPL" in captured.out
    assert "SAP" in captured.out
    assert "Depotwert" in captured.out


def test_print_portfolio_outputs_empty_message(capsys):
    print_portfolio({})

    captured = capsys.readouterr()
    assert "Keine Positionen im virtuellen Depot." in captured.out


def test_print_closed_trades_outputs_metadata_and_trade_data(capsys):
    trades = [
        {
            "buy_time": "2026-03-20 10:00:00",
            "sell_time": "2026-03-21 10:00:00",
            "pnl_eur": 15.0,
            "pnl_native": 16.0,
            "pnl_pct_eur": 1.5,
        }
    ]

    print_closed_trades(
        "CVX",
        "Chevron Corporation",
        "US1667641005",
        "852552",
        trades,
        "USD",
    )

    captured = capsys.readouterr()
    assert "DETAILS CVX" in captured.out
    assert "Chevron Corporation" in captured.out
    assert "US1667641005" in captured.out
    assert "852552" in captured.out


def test_print_financial_overview_outputs_expected_text(capsys):
    print_financial_overview(
        initial_cash_eur=9200.0,
        current_equity_eur=9500.0,
        pnl_eur=300.0,
        native_currency="USD",
        pnl_native=325.0,
    )

    captured = capsys.readouterr()
    assert "FINANZÜBERSICHT" in captured.out
    assert "Start" in captured.out
    assert "Stand" in captured.out
    assert "Differenz" in captured.out


def test_print_equity_curve_terminal_outputs_curve(capsys):
    equity_curve = [
        {"time": "2026-03-20", "equity_eur": 1000.0},
        {"time": "2026-03-21", "equity_eur": 1010.0},
        {"time": "2026-03-22", "equity_eur": 990.0},
        {"time": "2026-03-23", "equity_eur": 1030.0},
    ]

    print_equity_curve_terminal("AAPL", equity_curve)

    captured = capsys.readouterr()
    assert "DEPOTWERT-KURVE AAPL" in captured.out
    assert "Start:" in captured.out
    assert "Ende:" in captured.out
