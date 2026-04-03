from __future__ import annotations

import re
import unicodedata
from typing import Callable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

BI_SEARCH_URL = (
    "https://markets.businessinsider.com/ajax/"
    "SearchController_Suggest?max_results=8&query={query}"
)
BF_STOCK_URL = "https://www.boerse-frankfurt.de/aktie/{slug}"

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
WKN_RE = re.compile(r"^[A-Z0-9]{6}$")
BI_ENTRY_RE = re.compile(
    r'new Array\("(?P<name>[^"]+)",\s*"Stocks",\s*"(?P<symbol>[^"|]*)\|'
    r'(?P<isin>[A-Z0-9]{12})\|(?P<alt_symbol>[^"|]*)\|[^"]*"',
    re.IGNORECASE,
)
BF_TITLE_RE = re.compile(
    r"<title>\s*(?P<name>.*?)\s+Aktie\s+\|\s+(?P<wkn>[A-Z0-9]{6})\s+\|\s+"
    r"(?P<isin>[A-Z0-9]{12})\s+\|",
    re.IGNORECASE,
)

CORPORATE_SUFFIX_REPLACEMENTS = {
    "corporation": "corp",
    "incorporated": "inc",
    "company": "co",
    "limited": "ltd",
}


def _fetch_text(url: str, timeout: int = 8) -> str:
    req = Request(url, headers=HTTP_HEADERS)
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def is_valid_isin(value: str | None) -> bool:
    return bool(value and ISIN_RE.match(str(value).strip().upper()))


def is_valid_wkn(value: str | None) -> bool:
    return bool(value and WKN_RE.match(str(value).strip().upper()))


def _normalize_isin(value: str | None) -> str:
    text = str(value or "").strip().upper()
    return text if is_valid_isin(text) else "-"


def _normalize_wkn(value: str | None) -> str:
    text = str(value or "").strip().upper()
    return text if is_valid_wkn(text) else "-"


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().replace("&", " and ")
    ascii_text = ascii_text.replace("'", "").replace(".", " ").replace(",", " ")
    ascii_text = re.sub(r"\s+", " ", ascii_text).strip()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-")


def company_slug_candidates(company_name: str) -> list[str]:
    raw = str(company_name or "").strip()
    if not raw:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        slug = _slugify(text)
        if slug and slug not in seen:
            seen.add(slug)
            candidates.append(slug)

    add(raw)

    simplified = raw
    for source, target in CORPORATE_SUFFIX_REPLACEMENTS.items():
        simplified = re.sub(
            rf"\b{re.escape(source)}\b",
            target,
            simplified,
            flags=re.IGNORECASE,
        )
    add(simplified)

    return candidates


def lookup_business_insider_isin(
    symbol: str,
    fetcher: Callable[[str], str] = _fetch_text,
) -> str:
    normalized_symbol = str(symbol or "").strip().upper()
    if not normalized_symbol or "-" in normalized_symbol or "^" in normalized_symbol:
        return "-"

    try:
        payload = fetcher(BI_SEARCH_URL.format(query=quote_plus(normalized_symbol)))
    except Exception:
        return "-"

    fallback = "-"
    for match in BI_ENTRY_RE.finditer(payload):
        candidate_symbol = match.group("symbol").strip().upper()
        alt_symbol = match.group("alt_symbol").strip().upper()
        candidate_isin = _normalize_isin(match.group("isin"))
        if candidate_symbol == normalized_symbol:
            return candidate_isin
        if alt_symbol == normalized_symbol and fallback == "-":
            fallback = candidate_isin

    return fallback


def lookup_boerse_frankfurt_identifiers(
    company_name: str,
    fetcher: Callable[[str], str] = _fetch_text,
) -> dict[str, str]:
    for slug in company_slug_candidates(company_name):
        try:
            page = fetcher(BF_STOCK_URL.format(slug=slug))
        except Exception:
            continue

        match = BF_TITLE_RE.search(page)
        if not match:
            continue

        return {
            "name": match.group("name").strip(),
            "isin": _normalize_isin(match.group("isin")),
            "wkn": _normalize_wkn(match.group("wkn")),
            "slug": slug,
        }

    return {"name": "", "isin": "-", "wkn": "-", "slug": ""}


def resolve_identifiers(
    symbol: str,
    company_name: str = "",
    current_isin: str | None = None,
    current_wkn: str | None = None,
    fetcher: Callable[[str], str] = _fetch_text,
) -> dict[str, str]:
    isin = _normalize_isin(current_isin)
    wkn = _normalize_wkn(current_wkn)

    bi_isin = lookup_business_insider_isin(symbol, fetcher=fetcher)
    bf_data = lookup_boerse_frankfurt_identifiers(company_name, fetcher=fetcher) if company_name else {
        "isin": "-",
        "wkn": "-",
    }
    bf_isin = _normalize_isin(bf_data.get("isin"))
    bf_wkn = _normalize_wkn(bf_data.get("wkn"))

    if isin == "-" and bi_isin != "-":
        isin = bi_isin

    if isin == "-" and bf_isin != "-":
        isin = bf_isin

    if wkn == "-" and bf_wkn != "-":
        if isin == "-" or bf_isin == "-" or bf_isin == isin:
            wkn = bf_wkn

    return {
        "isin": isin,
        "wkn": wkn,
    }
