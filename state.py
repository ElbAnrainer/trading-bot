import json
import os
from config import STATE_FILE, BROKER_FILE


def load_json(file, default):
    if not os.path.exists(file):
        return default
    return json.load(open(file))


def save_json(file, data):
    json.dump(data, open(file, "w"), indent=2)


def load_state():
    return load_json(STATE_FILE, {"last_signal": 0})


def save_state(data):
    save_json(STATE_FILE, data)


def load_broker():
    return load_json(BROKER_FILE, {"cash": 10000, "position": 0})


def save_broker(data):
    save_json(BROKER_FILE, data)
