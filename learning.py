import json
import os

LEARNING_FILE = os.path.join("reports", "learned_scores.json")


def _ensure_dir():
    os.makedirs("reports", exist_ok=True)


def load_scores():
    _ensure_dir()
    if not os.path.exists(LEARNING_FILE):
        return {}

    try:
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
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
