from pathlib import Path

import github_actions_control as gac


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_get_auto_run_status_reads_active_workflow_state():
    calls = []

    def fake_runner(args, cwd=Path(".")):
        calls.append((args, cwd))
        return _Proc(
            stdout=(
                '[{"name":"Trading Bot Auto Run","path":".github/workflows/trading-bot.yml","state":"active"}]'
            )
        )

    result = gac.get_auto_run_status(
        cwd=Path("/tmp/repo"),
        runner=fake_runner,
        which=lambda name: "/usr/bin/gh",
    )

    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["label"] == "EIN"
    assert result["detail"] == "Workflow aktiv"
    assert calls[0][0] == ["workflow", "list", "--all", "--json", "name,path,state"]


def test_get_auto_run_status_maps_disabled_state_to_off():
    def fake_runner(args, cwd=Path(".")):
        return _Proc(
            stdout=(
                '[{"name":"Trading Bot Auto Run","path":".github/workflows/trading-bot.yml","state":"disabled_manually"}]'
            )
        )

    result = gac.get_auto_run_status(
        runner=fake_runner,
        which=lambda name: "/usr/bin/gh",
    )

    assert result["ok"] is True
    assert result["enabled"] is False
    assert result["label"] == "AUS"


def test_toggle_auto_run_disables_active_workflow():
    calls = []
    responses = [
        _Proc(stdout='[{"name":"Trading Bot Auto Run","path":".github/workflows/trading-bot.yml","state":"active"}]'),
        _Proc(stdout='[{"name":"Trading Bot Auto Run","path":".github/workflows/trading-bot.yml","state":"active"}]'),
        _Proc(),
        _Proc(stdout='[{"name":"Trading Bot Auto Run","path":".github/workflows/trading-bot.yml","state":"disabled_manually"}]'),
    ]

    def fake_runner(args, cwd=Path(".")):
        calls.append(args)
        return responses.pop(0)

    result = gac.toggle_auto_run(
        runner=fake_runner,
        which=lambda name: "/usr/bin/gh",
    )

    assert result["ok"] is True
    assert result["enabled"] is False
    assert result["changed"] is True
    assert result["message"] == "Auto-Run wurde ausgeschaltet."
    assert calls[2] == ["workflow", "disable", ".github/workflows/trading-bot.yml"]


def test_set_auto_run_enabled_returns_error_when_gh_is_missing():
    result = gac.set_auto_run_enabled(True, which=lambda name: None)

    assert result["ok"] is False
    assert result["label"] == "GH FEHLT"
    assert "nicht gefunden" in result["detail"]
