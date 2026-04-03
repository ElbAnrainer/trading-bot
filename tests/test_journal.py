import csv

import journal


def test_ensure_file_upgrades_existing_header(tmp_path, monkeypatch):
    journal_path = tmp_path / "trading_journal.csv"
    journal_path.write_text(
        "timestamp,symbol,company,signal,price_eur,score,reason,closed_trade,realized_pnl_eur\n"
        "2026-04-03T10:00:00,AAPL,Apple,BUY,100,80,test,false,0\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(journal, "JOURNAL_FILE", str(journal_path))

    journal.log_trade_decision(
        symbol="MSFT",
        company="Microsoft",
        isin="US5949181045",
        wkn="870747",
        signal="BUY",
        price_eur=120.0,
        score=75.0,
        reason="breakout",
    )

    with open(journal_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["isin"] == ""
    assert rows[0]["wkn"] == ""
    assert rows[1]["isin"] == "US5949181045"
    assert rows[1]["wkn"] == "870747"


def test_backfill_missing_identifiers_updates_existing_rows(tmp_path, monkeypatch):
    journal_path = tmp_path / "trading_journal.csv"
    journal_path.write_text(
        (
            "timestamp,symbol,company,isin,wkn,signal,price_eur,score,reason,closed_trade,realized_pnl_eur\n"
            "2026-04-03T10:00:00,AAPL,Apple Inc.,,,BUY,100,80,test,false,0\n"
            "2026-04-03T10:01:00,MSFT,Microsoft Corporation,,,BUY,120,75,test,false,0\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(journal, "JOURNAL_FILE", str(journal_path))

    changed = journal.backfill_missing_identifiers(
        lambda symbol, company: {
            "AAPL": {"isin": "US0378331005", "wkn": "865985"},
            "MSFT": {"isin": "US5949181045", "wkn": "870747"},
        }[symbol]
    )

    with open(journal_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert changed == 2
    assert rows[0]["isin"] == "US0378331005"
    assert rows[0]["wkn"] == "865985"
    assert rows[1]["isin"] == "US5949181045"
    assert rows[1]["wkn"] == "870747"
