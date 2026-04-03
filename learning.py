import json
import os

from config import LEARNED_SCORES_JSON, LEGACY_LEARNED_SCORES_JSON, ensure_reports_dir

LEARNING_FILE = LEARNED_SCORES_JSON


def _ensure_dir():
    ensure_reports_dir()


def _load_path():
    for path in (LEARNING_FILE, LEGACY_LEARNED_SCORES_JSON):
        if path and os.path.exists(path):
            return path
    return LEARNING_FILE


def load_scores():
    _ensure_dir()
    path = _load_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_scores(scores):
    _ensure_dir()
    with open(LEARNING_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)


def update_score(symbol, performance_score, alpha=0.3):
    """
    Exponential Moving Average (EMA Learning)

    alpha:
        0.1 = langsam lernen
        0.3 = gut
        0.7 = aggressiv
    """

    scores = load_scores()

    old = scores.get(symbol, performance_score)

    new = old * (1 - alpha) + performance_score * alpha

    scores[symbol] = round(new, 4)

    save_scores(scores)

    return new


def get_score(symbol):
    scores = load_scores()
    return scores.get(symbol)
