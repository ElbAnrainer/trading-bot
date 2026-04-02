"""Legacy compatibility alias for the historical module name typo."""

from portfolio import (
    allocate_capital,
    build_portfolio,
    normalize_weights,
    select_top_candidates,
)

__all__ = [
    "allocate_capital",
    "build_portfolio",
    "normalize_weights",
    "select_top_candidates",
]
