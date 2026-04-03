from identifier_lookup import (
    company_slug_candidates,
    lookup_boerse_frankfurt_identifiers,
    lookup_business_insider_isin,
    resolve_identifiers,
)


def test_lookup_business_insider_isin_prefers_exact_symbol():
    payload = (
        'mmSuggestDeliver(0, new Array("Name", "Category"), new Array('
        'new Array("Chevron Corp.", "Stocks", "CVX|US1667641005|CVX||CVX", "75", "", "cvx|CVX|1|988"),'
        'new Array("CVRx Inc Registered Shs", "Stocks", "CVRX|US1266381052|CVRX||", "75", "", "cvrx|CVRX|1|1")'
        '), 2, 0);'
    )

    assert lookup_business_insider_isin("CVX", fetcher=lambda url: payload) == "US1667641005"


def test_company_slug_candidates_include_common_suffix_variants():
    candidates = company_slug_candidates("Microsoft Corporation")

    assert "microsoft-corporation" in candidates
    assert "microsoft-corp" in candidates


def test_lookup_boerse_frankfurt_identifiers_uses_company_slug_variants():
    urls = []

    def fetcher(url):
        urls.append(url)
        if url.endswith("/microsoft-corp"):
            return "<title>Microsoft Corp. Aktie | 870747 | US5949181045 | Aktienkurs</title>"
        return "<title>Deutsche Börse: Aktien, Kurse, Charts und Nachrichten</title>"

    result = lookup_boerse_frankfurt_identifiers("Microsoft Corporation", fetcher=fetcher)

    assert urls[-1].endswith("/microsoft-corp")
    assert result["isin"] == "US5949181045"
    assert result["wkn"] == "870747"


def test_resolve_identifiers_combines_business_insider_and_boerse_frankfurt():
    def fetcher(url):
        if "SearchController_Suggest" in url:
            return (
                'mmSuggestDeliver(0, new Array("Name", "Category"), new Array('
                'new Array("Apple Inc.", "Stocks", "AAPL|US0378331005|AAPL||AAPL", "75", "", "aapl|AAPL|1|869")'
                '), 1, 0);'
            )
        if url.endswith("/apple-inc"):
            return "<title>Apple Inc. Aktie | 865985 | US0378331005 | Aktienkurs</title>"
        return ""

    result = resolve_identifiers("AAPL", "Apple Inc.", fetcher=fetcher)

    assert result == {"isin": "US0378331005", "wkn": "865985"}


def test_resolve_identifiers_does_not_mix_mismatched_isin_and_wkn():
    def fetcher(url):
        if "SearchController_Suggest" in url:
            return (
                'mmSuggestDeliver(0, new Array("Name", "Category"), new Array('
                'new Array("SAP SE (spons. ADRs)", "Stocks", "SAP|US8030542042|SAP||", "75", "", "sap|SAP|1|12299")'
                '), 1, 0);'
            )
        if url.endswith("/sap-se-spons-adrs"):
            return "<title>Deutsche Börse: Aktien, Kurse, Charts und Nachrichten</title>"
        if url.endswith("/sap-se"):
            return "<title>SAP SE Aktie | 716460 | DE0007164600 | Aktienkurs</title>"
        return ""

    result = resolve_identifiers("SAP", "SAP SE (spons. ADRs)", fetcher=fetcher)

    assert result == {"isin": "US8030542042", "wkn": "-"}
