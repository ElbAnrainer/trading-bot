from pathlib import Path

import walk_forward as wf


def test_run_walk_forward_uses_profile_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(wf, "REPORTS_DIR", Path(tmp_path))
    monkeypatch.setattr(wf, "WALK_FORWARD_DIR", Path(tmp_path) / "walk_forward")
    monkeypatch.setattr(wf, "_benchmark_return_pct", lambda period: 0.0)
    monkeypatch.setattr(wf, "_write_text", lambda summary, path: None)
    monkeypatch.setattr(wf, "_write_html", lambda summary, path: None)
    monkeypatch.setattr(wf, "_write_csv", lambda summary, path: None)
    monkeypatch.setattr(wf, "_write_json", lambda summary, path: None)
    monkeypatch.setattr(wf, "_write_xml", lambda summary, path: None)
    monkeypatch.setattr(wf, "_write_pdf", lambda summary, path: False)
    monkeypatch.setattr(wf, "get_active_profile_name", lambda: "mittel")
    monkeypatch.setattr(
        wf,
        "get_trading_config",
        lambda profile_name=None: {"max_positions": 6 if profile_name == "offensiv" else 4},
    )

    calls = []

    def fake_run_analysis(period, top_n, min_volume, long_mode, profile_name=None):
        calls.append(
            {
                "period": period,
                "top_n": top_n,
                "min_volume": min_volume,
                "profile_name": profile_name,
            }
        )
        return {"results": [], "future_candidates": []}

    monkeypatch.setattr(wf, "run_analysis", fake_run_analysis)

    summary = wf.run_walk_forward(
        periods=["1mo"],
        top_n=None,
        min_volume=123456,
        profile_name="offensiv",
    )

    assert calls[0]["top_n"] == 6
    assert calls[0]["min_volume"] == 123456
    assert calls[0]["profile_name"] == "offensiv"
    assert summary["profile_name"] == "offensiv"
    assert summary["top_n"] == 6
