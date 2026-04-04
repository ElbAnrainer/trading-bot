from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
AUTO_RUN_WORKFLOW_PATH = ".github/workflows/trading-bot.yml"
AUTO_RUN_WORKFLOW_NAME = "Trading Bot Auto Run"

STATUS_LABELS = {
    "active": "EIN",
    "disabled_manually": "AUS",
    "disabled_fork": "AUS",
    "disabled_inactivity": "AUS",
    "deleted": "GELÖSCHT",
}

STATUS_DETAILS = {
    "active": "Workflow aktiv",
    "disabled_manually": "Workflow manuell deaktiviert",
    "disabled_fork": "Workflow im Fork deaktiviert",
    "disabled_inactivity": "Workflow wegen Inaktivität deaktiviert",
    "deleted": "Workflow nicht mehr verfügbar",
}


def _result(
    *,
    ok: bool,
    state: str,
    enabled: bool | None,
    label: str,
    detail: str,
    changed: bool = False,
    message: str = "",
) -> dict[str, Any]:
    return {
        "ok": ok,
        "state": state,
        "enabled": enabled,
        "label": label,
        "detail": detail,
        "changed": changed,
        "message": message or detail,
    }


def _run_gh(args: list[str], cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _normalize_workflow_state(raw_state: str) -> tuple[bool | None, str, str]:
    state = str(raw_state or "").strip() or "unknown"
    if state == "active":
        return True, STATUS_LABELS["active"], STATUS_DETAILS["active"]
    if state.startswith("disabled"):
        return False, STATUS_LABELS.get(state, "AUS"), STATUS_DETAILS.get(state, state)
    return None, STATUS_LABELS.get(state, state.upper()), STATUS_DETAILS.get(state, state)


def get_auto_run_status(
    *,
    cwd: Path = PROJECT_ROOT,
    runner=_run_gh,
    which=shutil.which,
) -> dict[str, Any]:
    if which("gh") is None:
        return _result(
            ok=False,
            state="gh_missing",
            enabled=None,
            label="GH FEHLT",
            detail="GitHub CLI nicht gefunden",
        )

    proc = runner(["workflow", "list", "--all", "--json", "name,path,state"], cwd=cwd)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "GitHub API nicht erreichbar"
        return _result(
            ok=False,
            state="unavailable",
            enabled=None,
            label="UNBEKANNT",
            detail=detail,
        )

    try:
        workflows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        return _result(
            ok=False,
            state="invalid_json",
            enabled=None,
            label="UNBEKANNT",
            detail=f"Workflow-Status konnte nicht gelesen werden: {exc}",
        )

    for item in workflows:
        if item.get("path") == AUTO_RUN_WORKFLOW_PATH or item.get("name") == AUTO_RUN_WORKFLOW_NAME:
            enabled, label, detail = _normalize_workflow_state(str(item.get("state", "")))
            return _result(
                ok=True,
                state=str(item.get("state", "unknown")),
                enabled=enabled,
                label=label,
                detail=detail,
            )

    return _result(
        ok=False,
        state="not_found",
        enabled=None,
        label="NICHT GEFUNDEN",
        detail="Auto-Run-Workflow nicht gefunden",
    )


def set_auto_run_enabled(
    enable: bool,
    *,
    cwd: Path = PROJECT_ROOT,
    runner=_run_gh,
    which=shutil.which,
) -> dict[str, Any]:
    status = get_auto_run_status(cwd=cwd, runner=runner, which=which)
    if status["enabled"] is None:
        action = "einschalten" if enable else "ausschalten"
        status["message"] = f"Auto-Run konnte nicht {action} werden: {status['detail']}"
        return status

    if status["enabled"] is enable:
        state_text = "eingeschaltet" if enable else "ausgeschaltet"
        return _result(
            ok=True,
            state=status["state"],
            enabled=status["enabled"],
            label=status["label"],
            detail=status["detail"],
            changed=False,
            message=f"Auto-Run ist bereits {state_text}.",
        )

    command = "enable" if enable else "disable"
    proc = runner(["workflow", command, AUTO_RUN_WORKFLOW_PATH], cwd=cwd)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"gh workflow {command} fehlgeschlagen"
        return _result(
            ok=False,
            state="command_failed",
            enabled=None,
            label="FEHLER",
            detail=detail,
            changed=False,
            message=f"Auto-Run konnte nicht {'eingeschaltet' if enable else 'ausgeschaltet'} werden: {detail}",
        )

    refreshed = get_auto_run_status(cwd=cwd, runner=runner, which=which)
    if refreshed["enabled"] is enable:
        refreshed["changed"] = True
        refreshed["message"] = f"Auto-Run wurde {'eingeschaltet' if enable else 'ausgeschaltet'}."
        return refreshed

    return _result(
        ok=True,
        state=refreshed["state"],
        enabled=enable,
        label=refreshed["label"],
        detail=refreshed["detail"],
        changed=True,
        message=f"Auto-Run-Befehl ausgeführt. Neuer Status: {refreshed['label']}.",
    )


def toggle_auto_run(
    *,
    cwd: Path = PROJECT_ROOT,
    runner=_run_gh,
    which=shutil.which,
) -> dict[str, Any]:
    status = get_auto_run_status(cwd=cwd, runner=runner, which=which)
    if status["enabled"] is None:
        status["message"] = f"Auto-Run konnte nicht umgeschaltet werden: {status['detail']}"
        return status
    return set_auto_run_enabled(not bool(status["enabled"]), cwd=cwd, runner=runner, which=which)


def _status_line(result: dict[str, Any]) -> str:
    return f"{result['label']}|{result['detail']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GitHub Actions Auto-Run steuern")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("label")
    sub.add_parser("status-line")
    sub.add_parser("enable")
    sub.add_parser("disable")
    sub.add_parser("toggle")

    args = parser.parse_args(argv)

    if args.command == "label":
        result = get_auto_run_status()
        print(result["label"])
        return 0 if result["ok"] else 1

    if args.command == "status-line":
        result = get_auto_run_status()
        print(_status_line(result))
        return 0 if result["ok"] else 1

    if args.command == "enable":
        result = set_auto_run_enabled(True)
    elif args.command == "disable":
        result = set_auto_run_enabled(False)
    else:
        result = toggle_auto_run()

    print(result["message"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
