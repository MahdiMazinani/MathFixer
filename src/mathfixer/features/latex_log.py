from __future__ import annotations

import re

ERROR_BLOCK = re.compile(r"^! (?P<message>.+?)\n(?:.*\n){0,3}?l\.(?P<line>\d+)\s*(?P<context>.*)$", re.MULTILINE)
UNDEFINED_REFERENCE = re.compile(r"LaTeX Warning: Reference `([^']+)' .*?input line (\d+)", re.IGNORECASE)
FONT_WARNING = re.compile(r"LaTeX Font Warning:\s*(.+?)(?=\n\n|\Z)", re.DOTALL)
FILE_LINE_ERROR = re.compile(
    r"^(?P<file>[^:\n]+\.(?:tex|sty|cls)):(?P<line>\d+):\s*(?P<message>.+)$",
    re.MULTILINE | re.IGNORECASE,
)
FILE_EVENT = re.compile(r"\((?P<file>(?:\.{0,2}/)?[^()\s]+\.(?:tex|sty|cls))|(?P<close>\))", re.IGNORECASE)


def _file_at(log: str, offset: int) -> str | None:
    stack: list[str] = []
    for event in FILE_EVENT.finditer(log, 0, offset):
        if event.group("file"):
            stack.append(event.group("file"))
        elif stack:
            stack.pop()
    return stack[-1] if stack else None


def parse_latex_log(log: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    seen: set[tuple[str, str | None, int | None, str]] = set()
    for match in FILE_LINE_ERROR.finditer(log):
        message = match.group("message").strip()
        key = ("LATEX_COMPILE_ERROR", match.group("file"), int(match.group("line")), message)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            {
                "code": "LATEX_COMPILE_ERROR",
                "message": message,
                "suggestion": "Review the command at this exact project location and load any required package.",
                "file": match.group("file"),
                "line": int(match.group("line")),
                "severity": "error",
            }
        )
    for match in ERROR_BLOCK.finditer(log):
        message = match.group("message").strip()
        suggestion = "Review the command and load the package that defines it."
        if "Undefined control sequence" in message:
            suggestion = r"Check the command spelling and add the required \usepackage{...} declaration."
        file = _file_at(log, match.start())
        key = ("LATEX_COMPILE_ERROR", file, int(match.group("line")), message)
        if key not in seen:
            seen.add(key)
            findings.append({"code": "LATEX_COMPILE_ERROR", "message": message, "suggestion": suggestion, "file": file, "line": int(match.group("line")), "severity": "error"})
    for key, line in UNDEFINED_REFERENCE.findall(log):
        findings.append({"code": "UNDEFINED_REFERENCE", "message": f"Reference '{key}' is undefined.", "suggestion": "Add/correct the matching label and compile at least twice.", "file": None, "line": int(line), "severity": "warning"})
    for message in FONT_WARNING.findall(log):
        findings.append({"code": "FONT_WARNING", "message": " ".join(message.split()), "suggestion": "Choose an installed font with the required script and glyph coverage.", "file": None, "line": None, "severity": "warning"})
    return findings
