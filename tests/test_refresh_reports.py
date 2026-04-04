import refresh_reports


def test_run_refreshes_dashboard_daily_report_and_pdf(monkeypatch):
    calls = []

    monkeypatch.setattr(refresh_reports, "DASHBOARD_HTML", "/tmp/dashboard_latest.html")
    monkeypatch.setattr(refresh_reports, "DAILY_REPORT_TXT", "/tmp/daily_report_latest.txt")
    monkeypatch.setattr(refresh_reports, "TRADING_REPORT_PDF", "/tmp/trading_report_latest.pdf")

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

    assert calls == ["dashboard", "daily", "pdf"]
    assert paths == [
        "/tmp/dashboard_latest.html",
        "/tmp/daily_report_latest.txt",
        "/tmp/trading_report_latest.pdf",
    ]
