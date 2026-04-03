import json
import os

from config import BROKER_FILE, STATE_FILE


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
    return load_json(STATE_FILE, {"last_signal": 0})


def save_state(data):
    save_json(STATE_FILE, data)


def load_broker():
    return load_json(BROKER_FILE, {"cash": 10000, "position": 0})


def save_broker(data):
    save_json(BROKER_FILE, data)
