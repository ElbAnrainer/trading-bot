import sys

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
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    pdf_path = tmp_path / "report.pdf"
    html_path = reports_dir / "daily_report_latest.html"
    pdf_path.write_text("pdf", encoding="utf-8")
    html_path.write_text("<html></html>", encoding="utf-8")

    sent = {}

    def fake_send_report_email(attachment_paths):
        sent["attachments"] = attachment_paths

    monkeypatch.setattr(main, "send_report_email", fake_send_report_email)

    main._run_mail(True, str(pdf_path))

    assert sent["attachments"] == [
        str(pdf_path),
        "reports/daily_report_latest.html",
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
