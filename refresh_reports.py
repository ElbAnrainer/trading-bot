from __future__ import annotations

import json
from pathlib import Path

from config import DAILY_REPORT_TXT, DASHBOARD_HTML, LATEST_RUN_JSON, TRADING_REPORT_PDF
from decision_explanations import enrich_analysis_bundle
from daily_report import create_daily_report
from dashboard import build_dashboard
from report_pdf import run as build_pdf_report
from report_writer import update_latest_json_context


def _refresh_latest_run_explanations() -> None:
    latest_run_path = Path(LATEST_RUN_JSON)
    if not latest_run_path.exists():
        return

    try:
        snapshot = json.loads(latest_run_path.read_text(encoding="utf-8"))
    except Exception:
        return

    if not isinstance(snapshot, dict):
        return

    enriched_result, enriched_plan, enriched_decisions = enrich_analysis_bundle(
        snapshot,
        trading_plan=snapshot.get("trading_plan", []),
        decisions=snapshot.get("decisions", {}),
        profile_name=snapshot.get("profile_name"),
    )

    update_latest_json_context(
        latest_run_path.parent,
        profile_name=snapshot.get("profile_name"),
        results=enriched_result.get("results", []),
        portfolio=enriched_result.get("portfolio", {}),
        future_candidates=enriched_result.get("future_candidates", []),
        trading_plan=enriched_plan,
        decisions=enriched_decisions,
    )


def run() -> list[str]:
    paths: list[str] = []

    _refresh_latest_run_explanations()
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
