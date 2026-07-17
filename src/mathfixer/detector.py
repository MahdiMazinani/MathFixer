from __future__ import annotations

import re
from dataclasses import replace

from .models import DetectionMode, FormulaCandidate, FormulaKind
from .repair import repair_formula

_EXPLICIT_PATTERNS: tuple[tuple[re.Pattern[str], FormulaKind, bool, float], ...] = (
    (re.compile(r"\$\$(.+?)\$\$", re.DOTALL), FormulaKind.LATEX_DISPLAY, True, 0.99),
    (re.compile(r"\\\[(.+?)\\\]", re.DOTALL), FormulaKind.LATEX_DISPLAY, True, 0.99),
    (re.compile(r"\\\((.+?)\\\)", re.DOTALL), FormulaKind.LATEX_INLINE, False, 0.99),
    (re.compile(r"(?<!\\)(?<!\$)\$(?!\$)(.+?)(?<!\\)\$(?!\$)", re.DOTALL), FormulaKind.LATEX_INLINE, False, 0.98),
)
_ENVIRONMENT = re.compile(
    r"\\begin\{(?P<name>[A-Za-z*]+)\}.*?\\end\{(?P=name)\}", re.DOTALL
)
_LATEX_COMMAND = re.compile(
    r"\\(?:frac|dfrac|tfrac|sqrt|sum|prod|int|lim|begin|matrix|vec|hat|widehat|bar|overline|underline|alpha|beta|gamma|delta|theta|lambda|mu|rho|sigma|phi|chi|omega|text|mathrm|mathbf|mathbb|left|right)\b"
)
_MATH_SYMBOL = re.compile(r"[=<>≤≥≠≈±×÷∑∏∫√∞→←↔∂∇^_]|[⁰¹²³⁴-⁹₀-₉]|[α-ωΑ-Ω]")
_WORD = re.compile(r"[A-Za-z\u0600-\u06ff]{3,}")
_PERSIAN = re.compile(r"[\u0600-\u06ff]")
_PLAIN_EQUATION = re.compile(
    r"^\s*(?:[A-Za-zα-ωΑ-Ω][A-Za-z0-9_₀-₉⁰¹²³⁴-⁹]*(?:\s*\([^)]{0,80}\))?|[A-Za-z0-9_₀-₉⁰¹²³⁴-⁹()]+)\s*(?:=|≈|≤|≥|≠|:=|→)\s*.+$"
)


def _unescaped_dollar_count(text: str) -> int:
    return len(re.findall(r"(?<!\\)\$", text))


def _math_score(text: str) -> float:
    stripped = text.strip()
    if not stripped:
        return 0.0
    symbols = len(_MATH_SYMBOL.findall(stripped))
    commands = len(_LATEX_COMMAND.findall(stripped))
    digits = len(re.findall(r"\d", stripped))
    words = len(_WORD.findall(stripped))
    score = commands * 3.5 + symbols * 1.2 + min(digits, 8) * 0.15
    score -= max(0, words - 3) * 0.7
    if _PLAIN_EQUATION.match(stripped):
        score += 3.0
    if _PERSIAN.search(stripped) and len(stripped) > 80:
        score -= 3.0
    return score


def _is_broken_formula_paragraph(text: str) -> bool:
    stripped = text.strip()
    dollars = _unescaped_dollar_count(stripped)
    display_tokens = len(re.findall(r"(?<!\\)\$\$", stripped))
    proper_display = display_tokens == 2 and stripped.startswith("$$") and stripped.endswith("$$")
    if display_tokens and not proper_display and _math_score(stripped) >= 2.0:
        return True
    if dollars % 2 and _math_score(stripped) >= 4.0 and len(_WORD.findall(stripped)) <= 3:
        return True
    return (r"\begin{}" in stripped or r"\end{}" in stripped) and _math_score(stripped) >= 3.0


def _candidate(
    text: str,
    part: str,
    paragraph_index: int,
    start: int,
    end: int,
    kind: FormulaKind,
    display: bool,
    confidence: float,
) -> FormulaCandidate:
    source = text[start:end]
    normalized, repairs = repair_formula(
        source,
        plain_math=kind in {FormulaKind.UNICODE_MATH, FormulaKind.PLAIN_EQUATION},
    )
    return FormulaCandidate(
        part=part,
        paragraph_index=paragraph_index,
        start=start,
        end=end,
        source=source,
        normalized=normalized,
        kind=kind,
        display=display,
        confidence=confidence,
        repairs=repairs,
    )


def _overlaps(candidate: FormulaCandidate, existing: list[FormulaCandidate]) -> bool:
    return any(candidate.start < item.end and item.start < candidate.end for item in existing)


def detect_formulas(
    text: str,
    *,
    part: str,
    paragraph_index: int,
    mode: DetectionMode = DetectionMode.BALANCED,
) -> list[FormulaCandidate]:
    """Detect explicit TeX, damaged TeX, UnicodeMath and strict plain equations."""
    candidates: list[FormulaCandidate] = []
    if not text.strip():
        return candidates

    # Safe mode has a strict contract: only complete, explicit delimiters are accepted.
    # Conservative repair of malformed delimiters belongs to balanced/aggressive modes.
    if mode is not DetectionMode.SAFE and _is_broken_formula_paragraph(text):
        start = len(text) - len(text.lstrip())
        end = len(text.rstrip())
        return [
            _candidate(
                text,
                part,
                paragraph_index,
                start,
                end,
                FormulaKind.LATEX_BROKEN,
                True,
                0.92,
            )
        ]

    for pattern, kind, display, confidence in _EXPLICIT_PATTERNS:
        for match in pattern.finditer(text):
            item = _candidate(
                text,
                part,
                paragraph_index,
                match.start(),
                match.end(),
                kind,
                display,
                confidence,
            )
            if not _overlaps(item, candidates):
                candidates.append(item)

    if mode is DetectionMode.SAFE:
        return sorted(candidates, key=lambda item: item.start)

    for match in _ENVIRONMENT.finditer(text):
        item = _candidate(
            text,
            part,
            paragraph_index,
            match.start(),
            match.end(),
            FormulaKind.LATEX_ENVIRONMENT,
            True,
            0.96,
        )
        if not _overlaps(item, candidates):
            candidates.append(item)

    stripped = text.strip()
    leading = len(text) - len(text.lstrip())
    trailing = leading + len(stripped)
    whole_available = not any(item.start < trailing and leading < item.end for item in candidates)
    score = _math_score(stripped)

    if whole_available and _LATEX_COMMAND.search(stripped) and score >= 4.0:
        candidates.append(
            _candidate(
                text,
                part,
                paragraph_index,
                leading,
                trailing,
                FormulaKind.LATEX_RAW,
                len(stripped) > 24 or "=" in stripped,
                min(0.94, 0.76 + score / 50),
            )
        )
    elif whole_available and _PLAIN_EQUATION.match(stripped) and score >= 4.0:
        candidates.append(
            _candidate(
                text,
                part,
                paragraph_index,
                leading,
                trailing,
                FormulaKind.PLAIN_EQUATION,
                len(stripped) > 24,
                min(0.91, 0.72 + score / 45),
            )
        )
    elif (
        mode is DetectionMode.BALANCED
        and whole_available
        and _MATH_SYMBOL.search(stripped)
        and score >= 4.5
        and len(_WORD.findall(stripped)) <= 2
        and len(stripped) <= 160
    ):
        candidates.append(
            _candidate(
                text,
                part,
                paragraph_index,
                leading,
                trailing,
                FormulaKind.UNICODE_MATH,
                len(stripped) > 24,
                min(0.90, 0.74 + score / 55),
            )
        )
    elif (
        mode is DetectionMode.AGGRESSIVE
        and whole_available
        and _MATH_SYMBOL.search(stripped)
        and score >= 3.5
        and len(stripped) <= 240
    ):
        candidates.append(
            _candidate(
                text,
                part,
                paragraph_index,
                leading,
                trailing,
                FormulaKind.UNICODE_MATH,
                len(stripped) > 24,
                min(0.86, 0.67 + score / 55),
            )
        )

    candidates.sort(key=lambda item: (item.start, item.end))
    return [replace(item, candidate_id=f"{part}:{paragraph_index}:{i}") for i, item in enumerate(candidates)]
