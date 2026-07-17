from __future__ import annotations

import re

PERSIAN_TEXT = re.compile(r"[\u0600-\u06ff]")


def analyze_persian_latex(source: str) -> list[dict[str, str]]:
    if not PERSIAN_TEXT.search(source):
        return []
    findings: list[dict[str, str]] = []
    if "\\usepackage{xepersian}" not in source:
        findings.append({"code": "PERSIAN_PACKAGE", "message": "Persian text detected but xepersian is not loaded.", "suggestion": r"\usepackage{xepersian}"})
    if "\\settextfont" not in source:
        findings.append({"code": "PERSIAN_FONT", "message": "No Persian main font is configured.", "suggestion": r"\settextfont{Vazirmatn}"})
    if "\\setlatintextfont" not in source:
        findings.append({"code": "LATIN_FONT", "message": "No Latin companion font is configured.", "suggestion": r"\setlatintextfont{TeX Gyre Termes}"})
    if "\\begin{latin}" in source and "\\end{latin}" not in source:
        findings.append({"code": "BIDI_ENV", "message": "An unclosed latin environment may break bidirectional layout.", "suggestion": r"\end{latin}"})
    return findings
