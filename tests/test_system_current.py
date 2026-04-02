import importlib
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"


@pytest.fixture(autouse=True)
def _run_from_project_root(monkeypatch):
    monkeypatch.chdir(PROJECT_ROOT)


def test_required_modules_importable():
    modules = [
        "main",
        "analysis_engine",
        "output",
        "strategy",
        "data_loader",
        "journal",
        "performance",
        "dashboard",
        "cli",
        "broker",
    ]

    for module_name in modules:
        mod = importlib.import_module(module_name)
        assert mod is not None, f"Modul nicht importierbar: {module_name}"


def test_required_files_exist():
    required_files = [
        "main.py",
        "analysis_engine.py",
        "output.py",
        "strategy.py",
        "data_loader.py",
        "journal.py",
        "performance.py",
        "dashboard.py",
        "cli.py",
        "broker.py",
    ]

    for path in required_files:
        assert (PROJECT_ROOT / path).exists(), f"Datei fehlt: {path}"


def test_reports_directory_exists_or_can_be_created():
    REPORTS_DIR.mkdir(exist_ok=True)
    assert REPORTS_DIR.is_dir()


def test_dashboard_generation_runs():
    from dashboard import build_dashboard

    result = build_dashboard()

    assert isinstance(result, dict)
    assert (REPORTS_DIR / "dashboard_latest.json").exists()
    assert (REPORTS_DIR / "dashboard_latest.html").exists()


def test_performance_module_runs():
    from performance import analyze_performance

    result = analyze_performance()
    assert isinstance(result, dict)
    assert "ranking" in result
    assert "portfolio" in result
