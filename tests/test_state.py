import state


def test_load_state_returns_default_when_file_missing(monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(state, "STATE_FILE", str(state_path))

    assert state.load_state() == {"last_signal": 0}


def test_save_and_load_broker_roundtrip(monkeypatch, tmp_path):
    broker_path = tmp_path / "nested" / "broker.json"
    monkeypatch.setattr(state, "BROKER_FILE", str(broker_path))

    expected = {"cash": 1234.5, "position": 3}

    state.save_broker(expected)

    assert broker_path.exists()
    assert state.load_broker() == expected
