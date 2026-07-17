from __future__ import annotations

import re

ERROR_BLOCK = re.compile(r"^! (?P<message>.+?)\n(?:.*\n){0,3}?l\.(?P<line>\d+)\s*(?P<context>.*)$", re.MULTILINE)
UNDEFINED_REFERENCE = re.compile(r"LaTeX Warning: Reference `([^']+)' .*?input line (\d+)", re.IGNORECASE)
FONT_WARNING = re.compile(r"LaTeX Font Warning:\s*(.+?)(?=\n\n|\Z)", re.DOTALL)


def parse_latex_log(log: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for match in ERROR_BLOCK.finditer(log):
        message = match.group("message").strip()
        suggestion = "Review the command and load the package that defines it."
        if "Undefined control sequence" in message:
            suggestion = r"Check the command spelling and add the required \usepackage{...} declaration."
        findings.append({"code": "LATEX_COMPILE_ERROR", "message": message, "suggestion": suggestion, "line": int(match.group("line")), "severity": "error"})
    for key, line in UNDEFINED_REFERENCE.findall(log):
        findings.append({"code": "UNDEFINED_REFERENCE", "message": f"Reference '{key}' is undefined.", "suggestion": "Add/correct the matching label and compile at least twice.", "line": int(line), "severity": "warning"})
    for message in FONT_WARNING.findall(log):
        findings.append({"code": "FONT_WARNING", "message": " ".join(message.split()), "suggestion": "Choose an installed font with the required script and glyph coverage.", "line": None, "severity": "warning"})
    return findings
