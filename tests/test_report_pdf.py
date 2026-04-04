from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Table

import report_pdf


def test_build_top_symbols_table_uses_wrapped_cells_and_safe_widths():
    style = getSampleStyleSheet()["Normal"]
    rows = [
        {
            "symbol": "LYB",
            "isin": "NL0009434992",
            "wkn": "-",
            "company": "LyondellBasell Industries N.V.",
            "trades": 310,
            "pnl": 145548.71,
            "avg_score": 96.60,
        }
    ]

    table = report_pdf._build_top_symbols_table(rows, style)

    assert isinstance(table, Table)
    assert sum(table._argW) <= 17 * cm
    assert isinstance(table._cellvalues[1][3], Paragraph)
    assert isinstance(table._cellvalues[1][5], Paragraph)
    assert isinstance(table._cellvalues[1][6], Paragraph)
