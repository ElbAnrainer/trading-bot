import porfolio
import portfolio


def test_porfolio_alias_exports_portfolio_functions():
    assert porfolio.select_top_candidates is portfolio.select_top_candidates
    assert porfolio.normalize_weights is portfolio.normalize_weights
    assert porfolio.allocate_capital is portfolio.allocate_capital
    assert porfolio.build_portfolio is portfolio.build_portfolio


def test_porfolio_alias_behaves_like_portfolio_module():
    ranking = [
        {"symbol": "AAA", "learned_score": 3.0},
        {"symbol": "BBB", "learned_score": 1.0},
    ]

    result = porfolio.build_portfolio(ranking, top_n=2, capital=1000.0)

    assert [item["symbol"] for item in result] == ["AAA", "BBB"]
    assert sum(item["capital"] for item in result) == 1000.0
