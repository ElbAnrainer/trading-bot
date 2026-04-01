import math


def select_top_candidates(ranking, top_n=5):
    """
    Nimmt die Top N Aktien nach learned_score
    """
    if not ranking:
        return []

    return ranking[:top_n]


def normalize_weights(candidates):
    """
    Wandelt learned_score in Gewichte um (Summe = 1.0)
    """
    if not candidates:
        return []

    total_score = sum(max(float(c.get("learned_score", 0.0)), 0.0) for c in candidates)

    if total_score == 0:
        weight = 1 / len(candidates)
        for c in candidates:
            c["weight"] = weight
        return candidates

    for c in candidates:
        c["weight"] = max(float(c.get("learned_score", 0.0)), 0.0) / total_score

    return candidates


def allocate_capital(candidates, total_capital=1000.0):
    """
    Verteilt Kapital basierend auf Gewicht
    """
    for c in candidates:
        c["capital"] = round(float(c.get("weight", 0.0)) * total_capital, 2)

    return candidates


def build_portfolio(ranking, top_n=5, capital=1000.0):
    """
    Komplett-Pipeline:
    1. Top N auswählen
    2. Gewichte normalisieren
    3. Kapital zuweisen
    """
    candidates = select_top_candidates(ranking, top_n=top_n)
    candidates = normalize_weights(candidates)
    candidates = allocate_capital(candidates, total_capital=capital)
    return candidates
