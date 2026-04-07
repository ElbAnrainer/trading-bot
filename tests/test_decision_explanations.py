from decision_explanations import enrich_analysis_bundle


def test_enrich_analysis_bundle_adds_explanations_to_candidates_plan_and_orders():
    analysis_result = {
        "future_candidates": [
            {
                "symbol": "MSFT",
                "company_name": "Microsoft Corporation",
                "isin": "US5949181045",
                "wkn": "870747",
                "future_signal": "BUY",
                "score": 71.5,
                "strength": "stark",
                "risk": "mittel",
                "reasons": ["über SMA50", "Breakout", "Momentum positiv"],
                "relative_strength_pct": 3.2,
                "volatility_pct": 2.1,
                "learned_bonus": 4.0,
                "learned_confidence": 0.8,
            }
        ],
        "results": [
            {
                "symbol": "MSFT",
                "company_name": "Microsoft Corporation",
                "signal": "BUY",
                "score": 71.5,
                "trade_count": 8,
                "pnl_eur": 420.0,
            }
        ],
    }
    trading_plan = [
        {
            "symbol": "MSFT",
            "capital": 250.0,
            "weight": 0.25,
            "learned_score": 88.0,
        }
    ]
    decisions = {
        "orders": [
            {
                "action": "BUY",
                "symbol": "MSFT",
                "reason": "BUY_TOP_SELECTION",
                "capital": 250.0,
                "weight": 0.25,
                "learned_score": 88.0,
            }
        ],
        "drawdown_state": {},
        "risk": {},
    }

    result, plan, enriched_decisions = enrich_analysis_bundle(
        analysis_result,
        trading_plan=trading_plan,
        decisions=decisions,
        profile_name="konservativ",
    )

    assert result["future_candidates"][0]["explanation_summary"].startswith("Kaufsignal")
    assert result["future_candidates"][0]["explanation_points"]
    assert result["results"][0]["explanation_summary"].startswith("Kaufsignal")
    assert plan[0]["explanation_summary"].startswith("Im Trading-Plan")
    assert enriched_decisions["orders"][0]["reason_label"] == "Top-Auswahl mit Kaufsignal"
    assert enriched_decisions["orders"][0]["explanation_summary"].startswith("Kaufauftrag")
