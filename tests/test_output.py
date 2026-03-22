from output import print_human, print_technical


def test_print_human_outputs_readable_text(capsys):
    summary = {
        "cash": 9007.24,
        "position": 4,
        "avg_entry": 248.19,
        "equity": 10000.00,
    }

    print_human("AAPL", "Apple Inc.", "865985", "BUY", 4, 248.19, summary)

    captured = capsys.readouterr()
    assert "Apple Inc." in captured.out
    assert "WKN: 865985" in captured.out
    assert "KAUFEN" in captured.out


def test_print_technical_outputs_payload(capsys):
    payload = {"signal": "BUY", "qty": 4}
    print_technical(payload)

    captured = capsys.readouterr()
    assert "TECH:" in captured.out
    assert "BUY" in captured.out
