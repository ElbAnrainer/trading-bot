import csv
import json
import math
from collections import defaultdict
from pathlib import Path


JOURNAL_FILE_CANDIDATES = [
    Path("reports/trading_journal.csv"),
    Path("trading_journal.csv"),
]

MODEL_FILE = Path(".cache/learned_score_model.json")


def _find_journal_file():
    for path in JOURNAL_FILE_CANDIDATES:
        if path.exists():
            return path
    return JOURNAL_FILE_CANDIDATES[0]


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bounded(value, lower, upper):
    return max(lower, min(upper, value))


def _load_rows():
    journal_file = _find_journal_file()

    if not journal_file.exists():
        return []

    with open(journal_file, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_learning_model(min_trades=3):
    rows = _load_rows()

    per_symbol = defaultdict(
        lambda: {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "pnl_total": 0.0,
            "scores": [],
        }
    )

    for row in rows:
        symbol = (row.get("symbol") or "").strip().upper()
        if not symbol:
            continue

        score = _to_float(row.get("score"), None)
        if score is not None:
            per_symbol[symbol]["scores"].append(score)

        is_closed_trade = str(row.get("closed_trade", "")).strip().lower() == "true"
        if not is_closed_trade:
            continue

        pnl = _to_float(row.get("realized_pnl_eur"), 0.0)
        per_symbol[symbol]["trades"] += 1
        per_symbol[symbol]["pnl_total"] += pnl

        if pnl > 0:
            per_symbol[symbol]["wins"] += 1
        elif pnl < 0:
            per_symbol[symbol]["losses"] += 1

    model = {}

    for symbol, data in per_symbol.items():
        trades = data["trades"]
        if trades < min_trades:
            continue

        avg_pnl = data["pnl_total"] / trades if trades else 0.0
        hit_rate = (data["wins"] / trades) * 100.0 if trades else 0.0
        avg_score = (
            sum(data["scores"]) / len(data["scores"])
            if data["scores"]
            else 0.0
        )

        confidence = min(1.0, trades / 12.0)

        pnl_component = _bounded(avg_pnl / 5.0, -10.0, 10.0)
        hit_component = _bounded((hit_rate - 50.0) / 5.0, -10.0, 10.0)

        raw_bonus = (pnl_component + hit_component) * confidence
        learned_bonus = _bounded(raw_bonus, -20.0, 20.0)

        model[symbol] = {
            "trades": trades,
            "wins": data["wins"],
            "losses": data["losses"],
            "pnl_total": round(data["pnl_total"], 2),
            "avg_pnl": round(avg_pnl, 2),
            "hit_rate": round(hit_rate, 2),
            "avg_score": round(avg_score, 2),
            "confidence": round(confidence, 3),
            "learned_bonus": round(learned_bonus, 2),
        }

    return model


def save_learning_model(model):
    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)


def load_learning_model():
    if not MODEL_FILE.exists():
        return {}
    try:
        with open(MODEL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def refresh_learning_model(min_trades=3):
    model = build_learning_model(min_trades=min_trades)
    save_learning_model(model)
    return model


def apply_learning_to_candidates(candidates, min_trades=3):
    model = refresh_learning_model(min_trades=min_trades)
    updated = []

    for item in candidates:
        new_item = dict(item)

        symbol = str(new_item.get("symbol", "")).strip().upper()
        learned = model.get(symbol, {})

        base_score = float(new_item.get("score", 0.0))
        learned_bonus = float(learned.get("learned_bonus", 0.0))
        adjusted_score = base_score + learned_bonus

        new_item["score_before_learning"] = round(base_score, 2)
        new_item["learned_bonus"] = round(learned_bonus, 2)
        new_item["learned_confidence"] = float(learned.get("confidence", 0.0))
        new_item["learned_hit_rate"] = float(learned.get("hit_rate", 0.0))
        new_item["learned_avg_pnl"] = float(learned.get("avg_pnl", 0.0))
        new_item["score"] = round(adjusted_score, 2)

        reasons = list(new_item.get("reasons", []))
        if learned:
            reasons.append(
                f"Lernbonus {learned_bonus:+.2f} "
                f"(Treffer {learned.get('hit_rate', 0.0):.1f}%, "
                f"Ø P/L {learned.get('avg_pnl', 0.0):.2f} EUR, "
                f"Trades {learned.get('trades', 0)})"
            )
        else:
            reasons.append("Kein Lernbonus (zu wenig Historie)")
        new_item["reasons"] = reasons

        updated.append(new_item)

    return updated


def print_learning_summary():
    model = refresh_learning_model()

    print("\n==============================")
    print("SELBSTLERNENDER SCORE")
    print("------------------------------")

    if not model:
        print("Noch nicht genug Historie für Lernbonus.")
        print("==============================\n")
        return

    ranked = sorted(
        model.items(),
        key=lambda x: x[1].get("learned_bonus", 0.0),
        reverse=True,
    )

    for symbol, data in ranked[:10]:
        print(
            f"{symbol}: Bonus {data['learned_bonus']:+.2f} | "
            f"Treffer {data['hit_rate']:.1f}% | "
            f"Ø P/L {data['avg_pnl']:.2f} EUR | "
            f"Trades {data['trades']}"
        )

    print("==============================\n")
