from __future__ import annotations

from typing import Any

from config import get_trading_config


_ORDER_REASON_LABELS = {
    "BUY_TOP_SELECTION": "Top-Auswahl mit Kaufsignal",
    "WATCH_TOP_SELECTION": "Top-Auswahl trotz Watch-Signal",
    "HOLD_TOP_SELECTION": "Top-Auswahl ohne klares Kaufsignal",
    "BUY_SIGNAL_TOP_SELECTION": "Top-Auswahl mit aktivem Buy-Signal",
    "SELL_SIGNAL": "Verkaufssignal",
    "NOT_IN_TOP_SELECTION": "Nicht mehr in der Top-Auswahl",
    "STOP_LOSS": "Stop-Loss ausgelöst",
    "TAKE_PROFIT": "Take-Profit ausgelöst",
}


def _safe_text(value: Any, default: str = "-") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _reason_list(item: dict[str, Any]) -> list[str]:
    reasons = item.get("reasons", [])
    if not isinstance(reasons, list):
        return []
    return [str(reason).strip() for reason in reasons if str(reason).strip()]


def order_reason_label(reason_code: Any) -> str:
    code = _safe_text(reason_code, "")
    if not code:
        return "-"
    return _ORDER_REASON_LABELS.get(code, code.replace("_", " ").title())


def _signal_summary(signal: str, reasons: list[str], score: float | None) -> str:
    if signal == "BUY":
        if reasons:
            return f"Kaufsignal wegen {', '.join(reasons[:3])}."
        if score is not None:
            return f"Kaufsignal mit {score:.2f} Punkten und stabilem Marktbild."
        return "Kaufsignal mit positiver Trend- und Score-Lage."

    if signal == "WATCH":
        if reasons:
            return f"Beobachtungskandidat wegen {', '.join(reasons[:3])}, aber noch kein klarer Einstieg."
        if score is not None:
            return f"Beobachtungskandidat mit {score:.2f} Punkten, aber noch ohne klares Kaufsignal."
        return "Beobachtungskandidat ohne klares Einstiegssignal."

    if signal == "SELL":
        if reasons:
            return f"Verkaufssignal, obwohl zuletzt noch {', '.join(reasons[:2])} sichtbar waren."
        return "Verkaufssignal, weil Trend oder Momentum nicht mehr tragen."

    if signal == "HOLD":
        if reasons:
            return f"Abwarten, obwohl {', '.join(reasons[:2])} positiv wirken."
        return "Abwarten, weil weder Kauf- noch Verkaufssignal eindeutig sind."

    return "Keine klare Signal-Erklärung verfügbar."


def _candidate_points(item: dict[str, Any], profile_name: str | None = None) -> list[str]:
    cfg = get_trading_config(profile_name)
    reasons = _reason_list(item)
    points: list[str] = []

    if reasons:
        points.append("These: " + ", ".join(reasons[:3]))

    quality_bits: list[str] = []
    score = _safe_float(item.get("score"))
    strength = _safe_text(item.get("strength"), "")
    risk = _safe_text(item.get("risk"), "")
    if score is not None:
        quality_bits.append(f"Score {score:.2f}")
    if strength and strength != "-":
        quality_bits.append(f"Stärke {strength}")
    if risk and risk != "-":
        quality_bits.append(f"Risiko {risk}")
    if quality_bits:
        points.append("Qualität: " + " | ".join(quality_bits))

    market_bits: list[str] = []
    rs = _safe_float(item.get("relative_strength_pct"))
    vol = _safe_float(item.get("volatility_pct"))
    if rs is not None:
        market_bits.append(f"Relative Stärke {rs:+.2f}%")
    if vol is not None:
        market_bits.append(f"Volatilität 20 {vol:.2f}%")
    if market_bits:
        points.append("Marktbild: " + " | ".join(market_bits))

    profile_bits: list[str] = []
    stop_loss_pct = _safe_float(cfg.get("stop_loss_pct"))
    max_position_pct = _safe_float(cfg.get("max_position_pct"))
    min_expected_edge_pct = _safe_float(cfg.get("min_expected_edge_pct"))
    if stop_loss_pct is not None:
        profile_bits.append(f"Stop-Loss {stop_loss_pct * 100:.1f}%")
    if max_position_pct is not None:
        profile_bits.append(f"Max Position {max_position_pct * 100:.0f}%")
    if min_expected_edge_pct is not None:
        profile_bits.append(f"Min Edge {min_expected_edge_pct * 100:.1f}%")
    if profile_bits:
        points.append("Profil: " + " | ".join(profile_bits))

    learning_bits: list[str] = []
    learned_bonus = _safe_float(item.get("learned_bonus"))
    learned_confidence = _safe_float(item.get("learned_confidence"))
    if learned_bonus is not None and abs(learned_bonus) >= 0.01:
        learning_bits.append(f"Learning-Bonus {learned_bonus:+.2f}")
    if learned_confidence is not None and learned_confidence > 0:
        learning_bits.append(f"Konfidenz {learned_confidence:.2f}")
    if learning_bits:
        points.append("Lernen: " + " | ".join(learning_bits))

    return points[:4]


def _company_name(item: dict[str, Any]) -> str:
    return _safe_text(item.get("company_name") or item.get("company") or item.get("symbol"), "-")


def enrich_candidate(item: dict[str, Any], profile_name: str | None = None) -> dict[str, Any]:
    enriched = dict(item)
    signal = _safe_text(enriched.get("future_signal") or enriched.get("signal"))
    reasons = _reason_list(enriched)
    score = _safe_float(enriched.get("score"))

    enriched["company_name"] = _company_name(enriched)
    enriched["reasons"] = reasons
    enriched["explanation_summary"] = _signal_summary(signal, reasons, score)
    enriched["explanation_points"] = _candidate_points(enriched, profile_name=profile_name)
    return enriched


def enrich_result(item: dict[str, Any], candidate_lookup: dict[str, dict[str, Any]], profile_name: str | None = None) -> dict[str, Any]:
    enriched = dict(item)
    candidate = candidate_lookup.get(_safe_text(item.get("symbol"), ""))
    if candidate:
        for key in (
            "reasons",
            "strength",
            "risk",
            "relative_strength_pct",
            "volatility_pct",
            "score_before_learning",
            "learned_bonus",
            "learned_confidence",
        ):
            if key in candidate and key not in enriched:
                enriched[key] = candidate[key]

    signal = _safe_text(enriched.get("signal"))
    reasons = _reason_list(enriched)
    score = _safe_float(enriched.get("score"))
    trade_count = int(_safe_float(enriched.get("trade_count"), 0.0) or 0)
    pnl_eur = _safe_float(enriched.get("pnl_eur"), 0.0) or 0.0

    summary = _signal_summary(signal, reasons, score)
    summary = summary.rstrip(".") + f" Backtest: {trade_count} Trades, P/L {pnl_eur:.2f} EUR."

    points = _candidate_points(enriched, profile_name=profile_name)
    if trade_count > 0:
        points = [f"Backtest: {trade_count} Trades | P/L {pnl_eur:.2f} EUR"] + points

    enriched["company_name"] = _company_name(enriched)
    enriched["reasons"] = reasons
    enriched["explanation_summary"] = summary
    enriched["explanation_points"] = points[:4]
    return enriched


def enrich_trading_plan(
    plan: list[dict[str, Any]] | Any,
    analysis_result: dict[str, Any] | None,
    profile_name: str | None = None,
) -> list[dict[str, Any]]:
    enriched_plan: list[dict[str, Any]] = []
    if not isinstance(plan, list):
        return enriched_plan

    candidates = analysis_result.get("future_candidates", []) if isinstance(analysis_result, dict) else []
    results = analysis_result.get("results", []) if isinstance(analysis_result, dict) else []
    lookup = {
        _safe_text(item.get("symbol"), ""): item
        for item in [*candidates, *results]
        if _safe_text(item.get("symbol"), "")
    }

    for item in plan or []:
        enriched = dict(item)
        symbol = _safe_text(enriched.get("symbol"), "")
        match = lookup.get(symbol, {})

        for key in ("company_name", "company", "isin", "wkn", "strength", "risk", "reasons"):
            if key in match and not enriched.get(key):
                enriched[key] = match.get(key)

        signal = _safe_text(match.get("future_signal") or match.get("signal"), "-")
        weight = (_safe_float(enriched.get("weight"), 0.0) or 0.0) * 100.0
        capital = _safe_float(enriched.get("capital"), 0.0) or 0.0
        learned_score = _safe_float(enriched.get("learned_score"), 0.0) or 0.0

        if match:
            base_summary = _safe_text(match.get("explanation_summary"), "")
            summary = (
                f"Im Trading-Plan mit {weight:.1f}% Gewicht und {capital:.2f} EUR. "
                f"{base_summary if base_summary else 'Der aktuelle Kandidat überzeugt.'}"
            )
        else:
            summary = (
                f"Im Trading-Plan wegen starkem historischem Learned Score ({learned_score:.2f}) "
                f"mit {weight:.1f}% Gewicht und {capital:.2f} EUR."
            )

        points = [f"Allokation: {weight:.1f}% = {capital:.2f} EUR", f"Learned Score {learned_score:.2f}"]
        for point in match.get("explanation_points", [])[:2]:
            if point not in points:
                points.append(point)

        enriched["company"] = _company_name(enriched)
        enriched["signal"] = signal
        enriched["reasons"] = _reason_list(match)
        enriched["explanation_summary"] = summary.rstrip(".") + "."
        enriched["explanation_points"] = points[:4]
        enriched_plan.append(enriched)

    return enriched_plan


def enrich_decisions(
    decisions: dict[str, Any] | Any,
    analysis_result: dict[str, Any] | None,
    trading_plan: list[dict[str, Any]] | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    if not isinstance(decisions, dict):
        decisions = {}
    if not isinstance(trading_plan, list):
        trading_plan = []
    enriched = dict(decisions)
    orders_out: list[dict[str, Any]] = []

    candidates = analysis_result.get("future_candidates", []) if isinstance(analysis_result, dict) else []
    results = analysis_result.get("results", []) if isinstance(analysis_result, dict) else []
    lookup = {
        _safe_text(item.get("symbol"), ""): item
        for item in [*candidates, *results]
        if _safe_text(item.get("symbol"), "")
    }
    plan_lookup = {
        _safe_text(item.get("symbol"), ""): item
        for item in trading_plan or []
        if _safe_text(item.get("symbol"), "")
    }

    for item in decisions.get("orders", []) or []:
        order = dict(item)
        symbol = _safe_text(order.get("symbol"), "")
        match = lookup.get(symbol, {})
        planned = plan_lookup.get(symbol, {})

        reason_code = _safe_text(order.get("reason"))
        reason_label = order_reason_label(reason_code)
        action = _safe_text(order.get("action"))
        capital = _safe_float(order.get("capital"), 0.0) or 0.0
        weight = _safe_float(order.get("weight"), _safe_float(planned.get("weight"), 0.0)) or 0.0

        for key in ("company_name", "company", "isin", "wkn", "risk", "strength"):
            if key in match and not order.get(key):
                order[key] = match.get(key)

        if action == "BUY":
            base = _safe_text(match.get("explanation_summary"), "")
            if base and base != "-":
                summary = f"Kaufauftrag wegen {reason_label.lower()}; {base.rstrip('.')}. Einsatz {capital:.2f} EUR."
            else:
                summary = f"Kaufauftrag wegen {reason_label.lower()} mit {capital:.2f} EUR Einsatz."
        else:
            base = _safe_text(match.get("explanation_summary"), "")
            if base and base != "-":
                summary = f"Verkaufsauftrag wegen {reason_label.lower()}; {base.rstrip('.')}."
            else:
                summary = f"Verkaufsauftrag wegen {reason_label.lower()}."

        points = [f"Auslöser: {reason_label}"]
        if capital > 0:
            points.append(f"Kapital: {capital:.2f} EUR")
        if weight > 0:
            points.append(f"Plan-Gewicht: {weight * 100:.1f}%")
        for point in match.get("explanation_points", [])[:2]:
            if point not in points:
                points.append(point)

        order["company"] = _company_name(order)
        order["signal"] = _safe_text(match.get("future_signal") or match.get("signal"), "-")
        order["reasons"] = _reason_list(match)
        order["reason_label"] = reason_label
        order["weight"] = weight
        order["explanation_summary"] = summary.rstrip(".") + "."
        order["explanation_points"] = points[:4]
        orders_out.append(order)

    enriched["orders"] = orders_out
    return enriched


def enrich_analysis_bundle(
    analysis_result: dict[str, Any] | None,
    trading_plan: list[dict[str, Any]] | None = None,
    decisions: dict[str, Any] | None = None,
    profile_name: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    result = dict(analysis_result or {})

    future_candidates = [
        enrich_candidate(item, profile_name=profile_name)
        for item in result.get("future_candidates", []) or []
    ]
    candidate_lookup = {
        _safe_text(item.get("symbol"), ""): item
        for item in future_candidates
        if _safe_text(item.get("symbol"), "")
    }

    results = [
        enrich_result(item, candidate_lookup, profile_name=profile_name)
        for item in result.get("results", []) or []
    ]

    result["future_candidates"] = future_candidates
    result["results"] = results

    enriched_plan = enrich_trading_plan(trading_plan, result, profile_name=profile_name)
    enriched_decisions = enrich_decisions(
        decisions,
        result,
        trading_plan=enriched_plan,
        profile_name=profile_name,
    )

    return result, enriched_plan, enriched_decisions
