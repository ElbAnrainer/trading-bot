import re


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text):
    return ANSI_RE.sub("", str(text))


def visible_len(text):
    return len(strip_ansi(text))


def truncate_visible(text, width):
    text = str(text)
    if width is None or visible_len(text) <= width:
        return text
    return strip_ansi(text)[:width]


def pad_visible(text, width, align="<"):
    text = truncate_visible(text, width)
    if width is None:
        return text

    padding = max(0, width - visible_len(text))
    if align == ">":
        return (" " * padding) + text
    return text + (" " * padding)


def format_table_row(cells, separator=" | "):
    parts = []
    for cell in cells:
        if len(cell) == 2:
            text, width = cell
            align = "<"
        else:
            text, width, align = cell
        parts.append(pad_visible(text, width, align))
    return separator.join(parts)


def format_table_separator(cells, separator="-+-", fill="-"):
    pieces = []
    for cell in cells:
        width = cell[1]
        pieces.append(fill * max(3, int(width or 3)))
    return separator.join(pieces)
