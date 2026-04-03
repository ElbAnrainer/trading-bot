from __future__ import annotations

from typing import Any


def normalize_identifier(value: Any, default: str = "-") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else default


def identifiers_text(isin: Any = None, wkn: Any = None) -> str:
    return f"ISIN: {normalize_identifier(isin)} | WKN: {normalize_identifier(wkn)}"


def symbol_with_identifiers(symbol: Any, isin: Any = None, wkn: Any = None) -> str:
    return f"{normalize_identifier(symbol)} ({identifiers_text(isin, wkn)})"
