import output
import strategy
import data_loader
import main


def test_output_contract():
    required = [
        "print_summary_only",
        "print_ranking",
        "print_closed_trades",
        "print_recommendation",
        "print_portfolio",
        "print_financial_overview",
        "print_equity_curve_terminal",
        "print_future_candidates",
        "print_diagnostics",
    ]

    for name in required:
        assert hasattr(output, name), f"output.py fehlt Funktion: {name}"


def test_strategy_contract():
    required = [
        "add_signals",
        "compute_qty",
        "normalize_signal_from_row",
        "analyze_symbol",
        "stop_loss_price",
        "take_profit_price",
    ]

    for name in required:
        assert hasattr(strategy, name), f"strategy.py fehlt Funktion: {name}"


def test_data_loader_contract():
    required = [
        "load_data",
        "load_data_batch",
        "load_fx_to_eur_data",
        "latest_rate_to_eur",
        "fx_rate_to_eur_at",
        "fallback_rate_to_eur",
        "load_ticker_metadata",
        "fetch_dynamic_universe",
    ]

    for name in required:
        assert hasattr(data_loader, name), f"data_loader.py fehlt Funktion: {name}"


def test_main_contract():
    required = [
        "parse_args",
        "choose_interval",
        "normalize_period_input",
        "get_signal_from_df",
        "build_future_candidates",
        "run",
    ]

    for name in required:
        assert hasattr(main, name), f"main.py fehlt Funktion: {name}"
