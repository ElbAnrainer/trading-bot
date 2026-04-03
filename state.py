import json
import os

from config import BROKER_FILE, LEGACY_BROKER_FILE, LEGACY_STATE_FILE, STATE_FILE


def load_json(file, default):
    if not os.path.exists(file):
        return default

    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file, data):
    parent = os.path.dirname(file)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_state():
    path = STATE_FILE if os.path.exists(STATE_FILE) else LEGACY_STATE_FILE
    return load_json(path, {"last_signal": 0})


def save_state(data):
    save_json(STATE_FILE, data)


def load_broker():
    path = BROKER_FILE if os.path.exists(BROKER_FILE) else LEGACY_BROKER_FILE
    return load_json(path, {"cash": 10000, "position": 0})


def save_broker(data):
    save_json(BROKER_FILE, data)
