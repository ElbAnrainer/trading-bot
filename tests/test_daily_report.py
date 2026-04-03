from daily_report import _build_text_report


def _pipe_positions(text):
    return [idx for idx, char in enumerate(text) if char == "|"]


def test_build_text_report_aligns_top_stock_columns():
    report = {
        "generated_at": "2026-04-03 12:00:00",
        "total_entries": 10,
        "buy_signals": 1,
        "sell_signals": 2,
        "watch_signals": 3,
        "hold_signals": 4,
        "stocks_total": 5,
        "closed_trades": 6,
        "winning_trades": 4,
        "losing_trades": 2,
        "hit_rate": 66.67,
        "realized_pnl": 123.45,
        "avg_trade": 20.58,
        "top_symbols": [
            {
                "symbol": "AAPL",
                "company": "Apple Inc.",
                "isin": "US0378331005",
                "wkn": "865985",
                "count": 9,
            },
            {
                "symbol": "SAP",
                "company": "SAP SE",
                "isin": "DE0007164600",
                "wkn": "716460",
                "count": 3,
            },
        ],
    }

    text = _build_text_report(report)
    lines = text.splitlines()

    header = next(line for line in lines if "SYM" in line and "ANZAHL" in line)
    rows = [line for line in lines if line.startswith("AAPL") or line.startswith("SAP")]
    expected = _pipe_positions(header)

    assert "US0378331005" in text
    assert "716460" in text
    assert expected
    assert rows
    assert all(_pipe_positions(line) == expected for line in rows)
