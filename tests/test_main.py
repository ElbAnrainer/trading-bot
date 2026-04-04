import sys
from argparse import Namespace

import pandas as pd

import main


def test_choose_interval():
    assert main.choose_interval("1d") == "5m"
    assert main.choose_interval("5d") == "5m"
    assert main.choose_interval("1mo") == "5m"
    assert main.choose_interval("3mo") == "1h"
    assert main.choose_interval("1y") == "1d"
    assert main.choose_interval("3y") == "1d"


def test_normalize_period_input():
    assert main.normalize_period_input("1t") == "1d"
    assert main.normalize_period_input("1w") == "5d"
    assert main.normalize_period_input("1m") == "1mo"
    assert main.normalize_period_input("1j") == "1y"
    assert main.normalize_period_input("3j") == "3y"


def test_parse_args_period(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", "-l", "--top", "5", "--min-volume", "1000000", "--period", "1j"],
    )
    long_mode, top_n, min_volume, period_override = main.parse_args()

    assert long_mode is True
    assert top_n == 5
    assert min_volume == 1000000.0
    assert period_override == "1y"


def test_parse_args_accepts_pro_alias(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--pro"])
    pro_mode, top_n, min_volume, period_override = main.parse_args()

    assert pro_mode is True
    assert top_n == 5
    assert min_volume == 1000000
    assert period_override is None


def test_parse_cli_accepts_fast_mode(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--pro", "--fast"])

    args = main._parse_cli()

    assert args.pro_mode is True
    assert args.fast is True


def test_parse_cli_accepts_profile_and_compare(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--profile", "offensiv", "--compare-profiles", "--capital", "5000"])

    args = main._parse_cli()

    assert args.profile == "offensiv"
    assert args.compare_profiles is True
    assert args.capital == 5000.0


def test_get_signal_from_df():
    df = pd.DataFrame(
        {
            "Open": list(range(1, 261)),
            "High": [x + 1 for x in range(1, 261)],
            "Low": [x - 1 for x in range(1, 261)],
            "Close": list(range(1, 261)),
            "Volume": [10_000_000] * 260,
        }
    )

    signal, price_eur, price_native = main.get_signal_from_df(df, 0.9)

    assert signal in {"BUY", "SELL", "HOLD"}
    assert price_native == 260.0
    assert price_eur == 260.0 * 0.9


def test_build_future_candidates():
    analyzed = [
        {"symbol": "A", "score": 10},
        {"symbol": "B", "score": 50},
        {"symbol": "C", "score": 30},
    ]

    out = main.build_future_candidates(analyzed, 2)

    assert [x["symbol"] for x in out] == ["B", "C"]


def test_symbols_for_realistic_backtest_prefers_future_candidates():
    result = {
        "future_candidates": [
            {"symbol": "MSFT"},
            {"symbol": "AAPL"},
            {"symbol": "NVDA"},
        ],
        "results": [
            {"symbol": "TSLA"},
            {"symbol": "AMZN"},
        ],
    }

    assert main._symbols_for_realistic_backtest(result, 2) == ["MSFT", "AAPL"]


def test_symbols_for_realistic_backtest_falls_back_to_results():
    result = {
        "future_candidates": [{}, {"symbol": ""}],
        "results": [
            {"symbol": "TSLA"},
            {"symbol": "AMZN"},
            {"symbol": "META"},
        ],
    }

    assert main._symbols_for_realistic_backtest(result, 2) == ["TSLA", "AMZN"]


def test_run_mail_sends_pdf_and_html_attachment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    pdf_path = tmp_path / "report.pdf"
    html_path = tmp_path / "daily_report_latest.html"
    pdf_path.write_text("pdf", encoding="utf-8")
    html_path.write_text("<html></html>", encoding="utf-8")

    sent = {}

    def fake_send_report_email(attachment_paths):
        sent["attachments"] = attachment_paths

    monkeypatch.setattr(main, "send_report_email", fake_send_report_email)
    monkeypatch.setattr(main, "DAILY_REPORT_HTML", str(html_path))

    main._run_mail(True, str(pdf_path))

    assert sent["attachments"] == [
        str(pdf_path),
        str(html_path),
    ]


def test_run_mail_prints_error_when_pdf_missing(monkeypatch, capsys):
    called = {"value": False}

    def fake_send_report_email(attachment_paths):
        called["value"] = True

    monkeypatch.setattr(main, "send_report_email", fake_send_report_email)

    main._run_mail(True, None)

    out = capsys.readouterr().out
    assert "MAILVERSAND" in out
    assert "Mail-Fehler: Kein PDF vorhanden" in out
    assert called["value"] is False


def test_run_uses_pro_mode_for_analysis(monkeypatch):
    args = Namespace(
        dashboard=False,
        mini_system=False,
        live=False,
        pro_mode=True,
        beginner=False,
        top=4,
        period="1mo",
        min_volume=250000,
        long=False,
        fast=False,
        profile=None,
        compare_profiles=False,
        capital=None,
        skip_realistic_backtest=True,
        no_pdf=True,
        mail=False,
    )

    calls = {}

    monkeypatch.setattr(main, "_parse_cli", lambda: args)
    monkeypatch.setattr(main, "check_dependencies", lambda: True)
    monkeypatch.setattr(main, "get_active_profile_name", lambda: "mittel")
    monkeypatch.setattr(main, "set_pro_mode", lambda enabled: calls.setdefault("pro_mode", enabled))
    monkeypatch.setattr(main, "set_beginner_mode", lambda enabled: calls.setdefault("beginner_mode", enabled))
    monkeypatch.setattr(main, "run_live", lambda: (_ for _ in ()).throw(AssertionError("run_live should not be called")))

    def fake_run_analysis(**kwargs):
        calls["run_analysis"] = kwargs
        return {"future_candidates": [], "results": []}

    monkeypatch.setattr(main, "run_analysis", fake_run_analysis)
    monkeypatch.setattr(main, "build_trading_plan", lambda **kwargs: {})
    monkeypatch.setattr(main, "print_trading_plan", lambda plan: None)
    monkeypatch.setattr(main, "simulate_trading_decisions", lambda **kwargs: [])
    monkeypatch.setattr(main, "print_trading_decisions", lambda decisions: None)
    monkeypatch.setattr(main, "run_walk_forward", lambda **kwargs: None)
    monkeypatch.setattr(main, "print_performance", lambda: None)
    monkeypatch.setattr(main, "print_runtime", lambda runtime: None)
    monkeypatch.setattr(main, "print_explanations", lambda: None)
    monkeypatch.setattr(main, "update_latest_json_context", lambda **kwargs: None)
    monkeypatch.setattr(main, "build_dashboard", lambda **kwargs: None)
    monkeypatch.setattr(main, "_run_mail", lambda send_mail, pdf_path: None)

    main.run()

    assert calls["pro_mode"] is True
    assert calls["beginner_mode"] is False
    assert calls["run_analysis"]["long_mode"] is True
    assert calls["run_analysis"]["show_progress"] is True


def test_run_live_flag_keeps_live_mode_separate(monkeypatch):
    args = Namespace(
        dashboard=False,
        mini_system=False,
        live=True,
        pro_mode=False,
        beginner=False,
        top=5,
        period=None,
        min_volume=1000000,
        long=False,
        fast=False,
        profile=None,
        compare_profiles=False,
        capital=None,
        skip_realistic_backtest=False,
        no_pdf=False,
        mail=False,
    )

    called = {"live": False}

    monkeypatch.setattr(main, "_parse_cli", lambda: args)
    monkeypatch.setattr(main, "check_dependencies", lambda: True)
    monkeypatch.setattr(main, "run_live", lambda: called.__setitem__("live", True))
    monkeypatch.setattr(main, "run_analysis", lambda **kwargs: (_ for _ in ()).throw(AssertionError("run_analysis should not be called")))
    monkeypatch.setattr(main, "update_latest_json_context", lambda **kwargs: None)
    monkeypatch.setattr(main, "build_dashboard", lambda **kwargs: None)

    main.run()

    assert called["live"] is True


def test_run_fast_mode_skips_walk_forward_and_realistic_backtest(monkeypatch):
    args = Namespace(
        dashboard=False,
        mini_system=False,
        live=False,
        pro_mode=True,
        beginner=False,
        top=3,
        period="1mo",
        min_volume=1000000,
        long=False,
        fast=True,
        profile=None,
        compare_profiles=False,
        capital=None,
        skip_realistic_backtest=False,
        no_pdf=True,
        mail=False,
    )

    calls = {
        "walk_forward": 0,
        "realistic_backtest": 0,
    }

    monkeypatch.setattr(main, "_parse_cli", lambda: args)
    monkeypatch.setattr(main, "check_dependencies", lambda: True)
    monkeypatch.setattr(main, "get_active_profile_name", lambda: "mittel")
    monkeypatch.setattr(main, "set_pro_mode", lambda enabled: None)
    monkeypatch.setattr(main, "set_beginner_mode", lambda enabled: None)
    monkeypatch.setattr(main, "run_analysis", lambda **kwargs: {"future_candidates": [], "results": []})
    monkeypatch.setattr(main, "build_trading_plan", lambda **kwargs: {})
    monkeypatch.setattr(main, "print_trading_plan", lambda plan: None)
    monkeypatch.setattr(main, "simulate_trading_decisions", lambda **kwargs: [])
    monkeypatch.setattr(main, "print_trading_decisions", lambda decisions: None)
    monkeypatch.setattr(
        main,
        "run_walk_forward",
        lambda **kwargs: calls.__setitem__("walk_forward", calls["walk_forward"] + 1),
    )
    monkeypatch.setattr(
        main,
        "run_realistic_backtest",
        lambda **kwargs: calls.__setitem__("realistic_backtest", calls["realistic_backtest"] + 1),
    )
    monkeypatch.setattr(main, "print_realistic_backtest_summary", lambda realistic: None)
    monkeypatch.setattr(main, "print_performance", lambda: None)
    monkeypatch.setattr(main, "print_runtime", lambda runtime: None)
    monkeypatch.setattr(main, "print_explanations", lambda: None)
    monkeypatch.setattr(main, "update_latest_json_context", lambda **kwargs: None)
    monkeypatch.setattr(main, "build_dashboard", lambda **kwargs: None)
    monkeypatch.setattr(main, "_run_mail", lambda send_mail, pdf_path: None)

    main.run()

    assert calls["walk_forward"] == 0
    assert calls["realistic_backtest"] == 0


def test_build_profile_comparison_rows_uses_profile_specific_engine(monkeypatch):
    monkeypatch.setattr(main, "list_profile_names", lambda: ["konservativ", "offensiv"])
    monkeypatch.setattr(
        main,
        "get_trading_config",
        lambda profile_name: {
            "initial_capital": 10000.0 if profile_name == "konservativ" else 12000.0,
            "max_positions": 4 if profile_name == "konservativ" else 6,
            "max_position_pct": 0.2 if profile_name == "konservativ" else 0.3,
            "min_trade_eur": 400.0 if profile_name == "konservativ" else 200.0,
            "stop_loss_pct": 0.08 if profile_name == "konservativ" else 0.07,
            "max_drawdown_pct": 0.12 if profile_name == "konservativ" else 0.18,
        },
    )
    build_calls = []
    decision_calls = []
    monkeypatch.setattr(
        main,
        "build_trading_plan",
        lambda total_capital=1000.0, top_n=5, profile_name=None: build_calls.append(
            (profile_name, total_capital, top_n)
        ) or [{"symbol": profile_name.upper(), "capital": 100.0, "weight": 0.1}],
    )
    monkeypatch.setattr(
        main,
        "simulate_trading_decisions",
        lambda analysis_result, total_capital=1000.0, current_positions=None, peak_equity=None, top_n=None, profile_name=None: decision_calls.append(
            (profile_name, total_capital, top_n)
        ) or {
            "orders": [{"action": "BUY", "symbol": profile_name.upper()}],
            "drawdown_state": {"trading_blocked": profile_name == "konservativ"},
        },
    )

    rows = main._build_profile_comparison_rows(
        analysis_result={"future_candidates": [], "results": []},
        profile_names=["konservativ", "offensiv"],
    )

    assert rows[0]["profile_name"] == "konservativ"
    assert rows[0]["capital"] == 10000.0
    assert rows[0]["trading_blocked"] is True
    assert rows[1]["profile_name"] == "offensiv"
    assert rows[1]["capital"] == 12000.0
    assert rows[1]["buy_orders"] == 1
    assert build_calls == [
        ("konservativ", 10000.0, 4),
        ("offensiv", 12000.0, 6),
    ]
    assert decision_calls == [
        ("konservativ", 10000.0, 4),
        ("offensiv", 12000.0, 6),
    ]


def test_build_profile_comparison_rows_uses_explicit_capital_override(monkeypatch):
    monkeypatch.setattr(main, "list_profile_names", lambda: ["konservativ"])
    monkeypatch.setattr(
        main,
        "get_trading_config",
        lambda profile_name: {
            "initial_capital": 10000.0,
            "max_positions": 4,
            "max_position_pct": 0.2,
            "min_trade_eur": 400.0,
            "stop_loss_pct": 0.08,
            "max_drawdown_pct": 0.12,
        },
    )
    calls = {}

    def fake_build_trading_plan(total_capital=1000.0, top_n=5, profile_name=None):
        calls["build"] = (total_capital, top_n, profile_name)
        return []

    def fake_simulate_trading_decisions(
        analysis_result,
        total_capital=1000.0,
        current_positions=None,
        peak_equity=None,
        top_n=None,
        profile_name=None,
    ):
        calls["decisions"] = (total_capital, top_n, profile_name)
        return {"orders": [], "drawdown_state": {"trading_blocked": False}}

    monkeypatch.setattr(main, "build_trading_plan", fake_build_trading_plan)
    monkeypatch.setattr(main, "simulate_trading_decisions", fake_simulate_trading_decisions)

    rows = main._build_profile_comparison_rows(
        analysis_result={"future_candidates": [], "results": []},
        total_capital=5000.0,
        top_n=2,
        profile_names=["konservativ"],
    )

    assert rows[0]["capital"] == 5000.0
    assert calls["build"] == (5000.0, 2, "konservativ")
    assert calls["decisions"] == (5000.0, 2, "konservativ")


def test_run_uses_profile_override_for_core_calls(monkeypatch):
    args = Namespace(
        dashboard=False,
        mini_system=False,
        live=False,
        pro_mode=False,
        beginner=False,
        top=3,
        period="1mo",
        min_volume=250000,
        long=False,
        fast=False,
        profile="offensiv",
        compare_profiles=False,
        capital=5000.0,
        skip_realistic_backtest=False,
        no_pdf=True,
        mail=False,
    )

    calls = {}

    monkeypatch.setattr(main, "_parse_cli", lambda: args)
    monkeypatch.setattr(main, "check_dependencies", lambda: True)
    monkeypatch.setattr(main, "get_active_profile_name", lambda: "mittel")
    monkeypatch.setattr(main, "set_pro_mode", lambda enabled: None)
    monkeypatch.setattr(main, "set_beginner_mode", lambda enabled: None)
    monkeypatch.setattr(main, "print_trading_plan", lambda plan: None)
    monkeypatch.setattr(main, "print_trading_decisions", lambda decisions: None)
    monkeypatch.setattr(main, "print_realistic_backtest_summary", lambda realistic: None)
    monkeypatch.setattr(main, "print_performance", lambda: None)
    monkeypatch.setattr(main, "print_runtime", lambda runtime: None)
    monkeypatch.setattr(main, "print_explanations", lambda: None)
    monkeypatch.setattr(main, "_run_mail", lambda send_mail, pdf_path: None)
    monkeypatch.setattr(
        main,
        "get_trading_config",
        lambda profile_name: {"initial_capital": 10000.0, "max_positions": 6},
    )

    def fake_run_analysis(**kwargs):
        calls["run_analysis"] = kwargs
        return {"future_candidates": [{"symbol": "AAA"}], "results": [{"symbol": "AAA"}]}

    monkeypatch.setattr(main, "run_analysis", fake_run_analysis)

    def fake_build_trading_plan(**kwargs):
        calls["build_trading_plan"] = kwargs
        return []

    def fake_simulate_trading_decisions(**kwargs):
        calls["simulate_trading_decisions"] = kwargs
        return {"orders": [], "drawdown_state": {}, "risk": {}}

    monkeypatch.setattr(main, "build_trading_plan", fake_build_trading_plan)
    monkeypatch.setattr(main, "simulate_trading_decisions", fake_simulate_trading_decisions)
    monkeypatch.setattr(
        main,
        "update_latest_json_context",
        lambda **kwargs: calls.setdefault("update_latest_json_context", kwargs),
    )
    monkeypatch.setattr(main, "build_dashboard", lambda **kwargs: calls.setdefault("build_dashboard", kwargs))
    monkeypatch.setattr(main, "run_walk_forward", lambda **kwargs: calls.setdefault("run_walk_forward", kwargs))
    monkeypatch.setattr(main, "run_realistic_backtest", lambda **kwargs: calls.setdefault("run_realistic_backtest", kwargs) or {})

    main.run()

    assert calls["run_analysis"]["profile_name"] == "offensiv"
    assert calls["run_analysis"]["top_n"] == 3
    assert calls["build_trading_plan"]["profile_name"] == "offensiv"
    assert calls["build_trading_plan"]["total_capital"] == 5000.0
    assert calls["simulate_trading_decisions"]["profile_name"] == "offensiv"
    assert calls["simulate_trading_decisions"]["total_capital"] == 5000.0
    assert calls["update_latest_json_context"]["profile_name"] == "offensiv"
    assert calls["build_dashboard"]["profile_name"] == "offensiv"
    assert calls["run_walk_forward"]["profile_name"] == "offensiv"
    assert calls["run_walk_forward"]["top_n"] == 3
    assert calls["run_realistic_backtest"]["profile_name"] == "offensiv"


def test_run_defaults_to_profile_capital_and_max_positions(monkeypatch):
    args = Namespace(
        dashboard=False,
        mini_system=False,
        live=False,
        pro_mode=False,
        beginner=False,
        top=None,
        period="1mo",
        min_volume=250000,
        long=False,
        fast=False,
        profile="konservativ",
        compare_profiles=False,
        capital=None,
        skip_realistic_backtest=True,
        no_pdf=True,
        mail=False,
    )

    calls = {}

    monkeypatch.setattr(main, "_parse_cli", lambda: args)
    monkeypatch.setattr(main, "check_dependencies", lambda: True)
    monkeypatch.setattr(main, "set_pro_mode", lambda enabled: None)
    monkeypatch.setattr(main, "set_beginner_mode", lambda enabled: None)
    monkeypatch.setattr(main, "print_trading_plan", lambda plan: None)
    monkeypatch.setattr(main, "print_trading_decisions", lambda decisions: None)
    monkeypatch.setattr(main, "print_performance", lambda: None)
    monkeypatch.setattr(main, "print_runtime", lambda runtime: None)
    monkeypatch.setattr(main, "print_explanations", lambda: None)
    monkeypatch.setattr(main, "_run_mail", lambda send_mail, pdf_path: None)
    monkeypatch.setattr(main, "update_latest_json_context", lambda **kwargs: None)
    monkeypatch.setattr(main, "build_dashboard", lambda **kwargs: None)
    monkeypatch.setattr(main, "run_walk_forward", lambda **kwargs: None)
    monkeypatch.setattr(
        main,
        "get_trading_config",
        lambda profile_name: {"initial_capital": 12345.0, "max_positions": 4},
    )
    def fake_run_analysis(**kwargs):
        calls["run_analysis"] = kwargs
        return {"future_candidates": [], "results": []}

    def fake_build_trading_plan(**kwargs):
        calls["build_trading_plan"] = kwargs
        return []

    def fake_simulate_trading_decisions(**kwargs):
        calls["simulate_trading_decisions"] = kwargs
        return {"orders": [], "drawdown_state": {}, "risk": {}}

    monkeypatch.setattr(main, "run_analysis", fake_run_analysis)
    monkeypatch.setattr(main, "build_trading_plan", fake_build_trading_plan)
    monkeypatch.setattr(main, "simulate_trading_decisions", fake_simulate_trading_decisions)

    main.run()

    assert calls["run_analysis"]["top_n"] == 4
    assert calls["build_trading_plan"]["total_capital"] == 12345.0
    assert calls["build_trading_plan"]["top_n"] == 4
    assert calls["simulate_trading_decisions"]["total_capital"] == 12345.0
    assert calls["simulate_trading_decisions"]["top_n"] == 4
