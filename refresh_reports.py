from __future__ import annotations

from config import DAILY_REPORT_TXT, DASHBOARD_HTML, TRADING_REPORT_PDF
from daily_report import create_daily_report
from dashboard import build_dashboard
from report_pdf import run as build_pdf_report


def run() -> list[str]:
    paths: list[str] = []

    build_dashboard()
    paths.append(DASHBOARD_HTML)

    create_daily_report()
    paths.append(DAILY_REPORT_TXT)

    pdf_path = build_pdf_report()
    paths.append(pdf_path or TRADING_REPORT_PDF)

    return paths


def main() -> None:
    for path in run():
        print(path)


if __name__ == "__main__":
    main()
