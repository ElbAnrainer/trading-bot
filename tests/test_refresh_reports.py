import refresh_reports


def test_run_refreshes_dashboard_daily_report_and_pdf(monkeypatch):
    calls = []

    monkeypatch.setattr(refresh_reports, "DASHBOARD_HTML", "/tmp/dashboard_latest.html")
    monkeypatch.setattr(refresh_reports, "DAILY_REPORT_TXT", "/tmp/daily_report_latest.txt")
    monkeypatch.setattr(refresh_reports, "TRADING_REPORT_PDF", "/tmp/trading_report_latest.pdf")
    monkeypatch.setattr(refresh_reports, "_refresh_latest_run_explanations", lambda: calls.append("snapshot"))

    def fake_build_dashboard():
        calls.append("dashboard")

    def fake_create_daily_report():
        calls.append("daily")

    def fake_build_pdf_report():
        calls.append("pdf")
        return "/tmp/trading_report_latest.pdf"

    monkeypatch.setattr(refresh_reports, "build_dashboard", fake_build_dashboard)
    monkeypatch.setattr(refresh_reports, "create_daily_report", fake_create_daily_report)
    monkeypatch.setattr(refresh_reports, "build_pdf_report", fake_build_pdf_report)

    paths = refresh_reports.run()

    assert calls == ["snapshot", "dashboard", "daily", "pdf"]
    assert paths == [
        "/tmp/dashboard_latest.html",
        "/tmp/daily_report_latest.txt",
        "/tmp/trading_report_latest.pdf",
    ]


def test_refresh_latest_run_explanations_updates_snapshot(monkeypatch, tmp_path):
    latest_run = tmp_path / "latest_run.json"
    latest_run.write_text(
        '{"profile_name":"konservativ","results":[],"portfolio":{},"future_candidates":[{"symbol":"MSFT","future_signal":"BUY","score":70.0}],"trading_plan":[],"decisions":{"orders":[]}}',
        encoding="utf-8",
    )

    calls = {}

    monkeypatch.setattr(refresh_reports, "LATEST_RUN_JSON", str(latest_run))
    monkeypatch.setattr(
        refresh_reports,
        "enrich_analysis_bundle",
        lambda snapshot, trading_plan=None, decisions=None, profile_name=None: (
            {
                **snapshot,
                "future_candidates": [
                    {
                        "symbol": "MSFT",
                        "future_signal": "BUY",
                        "score": 70.0,
                        "explanation_summary": "Kaufsignal mit positiver Trendlage.",
                    }
                ],
            },
            [],
            {"orders": []},
        ),
    )
    monkeypatch.setattr(
        refresh_reports,
        "update_latest_json_context",
        lambda output_dir, **kwargs: calls.setdefault("update", (output_dir, kwargs)),
    )

    refresh_reports._refresh_latest_run_explanations()

    assert calls["update"][0] == tmp_path
    assert calls["update"][1]["future_candidates"][0]["explanation_summary"] == "Kaufsignal mit positiver Trendlage."
