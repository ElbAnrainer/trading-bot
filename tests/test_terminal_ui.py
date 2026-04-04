import terminal_ui


def test_cmd_pro_fast_uses_fast_pro_mode(monkeypatch):
    monkeypatch.setattr(terminal_ui, "CURRENT_PERIOD", "3mo")
    monkeypatch.setattr(terminal_ui, "CURRENT_TOP", 7)
    monkeypatch.setattr(terminal_ui, "CURRENT_MIN_VOLUME", 250000)
    monkeypatch.setattr(terminal_ui, "_python_bin", lambda: ".venv/bin/python")

    cmd = terminal_ui._cmd_pro_fast()

    assert cmd == [
        ".venv/bin/python",
        "main.py",
        "--pro",
        "--fast",
        "-p",
        "3mo",
        "-t",
        "7",
        "-mv",
        "250000",
    ]


def test_menu_items_expose_pro_fast_entry():
    assert ("Pro Schnell", "run_pro_fast") in terminal_ui.MENU_ITEMS


def test_menu_items_show_disable_label_when_auto_run_is_enabled():
    items = terminal_ui._menu_items({"enabled": True, "label": "EIN"})

    assert ("Auto-Run ausschalten", "toggle_auto_run") in items


def test_menu_items_show_enable_label_when_auto_run_is_disabled():
    items = terminal_ui._menu_items({"enabled": False, "label": "AUS"})

    assert ("Auto-Run einschalten", "toggle_auto_run") in items
