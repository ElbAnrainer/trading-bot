import performance


def test_load_filters_closed_trades_and_parses_numbers(tmp_path, monkeypatch):
    journal_path = tmp_path / "trading_journal.csv"
    journal_path.write_text(
        (
            "symbol,company,closed_trade,realized_pnl_eur,score\n"
            "AAPL,Apple,true,12.5,80\n"
            "MSFT,Microsoft,false,99.9,90\n"
            "NVDA,NVIDIA,TRUE,-3.0,abc\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(performance, "JOURNAL_PATHS", [str(tmp_path / "missing.csv"), str(journal_path)])

    trades, rows = performance._load()

    assert len(rows) == 3
    assert trades == [
        {
            "symbol": "AAPL",
            "company": "Apple",
            "isin": "-",
            "wkn": "-",
            "pnl": 12.5,
            "score": 80.0,
        },
        {
            "symbol": "NVDA",
            "company": "NVIDIA",
            "isin": "-",
            "wkn": "-",
            "pnl": -3.0,
            "score": 0.0,
        },
    ]


def test_analyze_performance_builds_sorted_ranking_and_portfolio(monkeypatch):
    monkeypatch.setattr(
        performance,
        "_load",
        lambda: (
            [
                {"symbol": "AAA", "company": "Alpha", "isin": "US0000000001", "wkn": "AAA111", "pnl": 10.0, "score": 70.0},
                {"symbol": "AAA", "company": "Alpha", "isin": "US0000000001", "wkn": "AAA111", "pnl": 5.0, "score": 80.0},
                {"symbol": "BBB", "company": "Beta", "isin": "US0000000002", "wkn": "BBB222", "pnl": -5.0, "score": 20.0},
            ],
            [
                {"symbol": "AAA", "signal": "BUY"},
                {"symbol": "AAA", "signal": "BUY"},
                {"symbol": "BBB", "signal": "SELL"},
                {"symbol": "CCC", "signal": "WATCH"},
                {"symbol": "DDD", "signal": "HOLD"},
            ],
        ),
    )

    updated = {}
    portfolio_inputs = {}

    def fake_update_score(symbol, perf):
        updated[symbol] = perf
        return perf + 1.0

    def fake_get_score(symbol):
        return None

    def fake_build_portfolio(ranking, top_n=5, capital=1000):
        portfolio_inputs["ranking"] = ranking
        return [{"symbol": ranking[0]["symbol"], "isin": ranking[0]["isin"], "wkn": ranking[0]["wkn"], "weight": 1.0, "capital": capital}]

    monkeypatch.setattr(performance, "update_score", fake_update_score)
    monkeypatch.setattr(performance, "get_score", fake_get_score)
    monkeypatch.setattr(performance, "build_portfolio", fake_build_portfolio)

    result = performance.analyze_performance()

    assert [item["symbol"] for item in result["ranking"]] == ["AAA", "BBB"]
    assert result["ranking"][0]["learned_score"] > result["ranking"][1]["learned_score"]
    assert result["ranking"][0]["avg_pnl"] == 7.5
    assert round(result["ranking"][0]["hit_rate"], 2) == 100.0
    assert result["ranking"][0]["isin"] == "US0000000001"
    assert result["ranking"][0]["wkn"] == "AAA111"
    assert updated["AAA"] > updated["BBB"]
    assert portfolio_inputs["ranking"] == result["ranking"]
    assert result["top_symbols"][0]["isin"] == "US0000000001"
    assert result["portfolio"] == [{"symbol": "AAA", "isin": "US0000000001", "wkn": "AAA111", "weight": 1.0, "capital": 1000}]
    assert result["total_entries"] == 5
    assert result["buy_signals"] == 2
    assert result["sell_signals"] == 1
    assert result["watch_signals"] == 1
    assert result["hold_signals"] == 1
    assert result["stocks_total"] == 4
