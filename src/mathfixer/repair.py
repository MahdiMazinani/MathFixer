from __future__ import annotations

import re
import unicodedata

_SUPERSCRIPTS = str.maketrans(
    {
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
        "⁺": "+",
        "⁻": "-",
        "⁼": "=",
        "ⁿ": "n",
    }
)
_SUBSCRIPTS = str.maketrans(
    {
        "₀": "0",
        "₁": "1",
        "₂": "2",
        "₃": "3",
        "₄": "4",
        "₅": "5",
        "₆": "6",
        "₇": "7",
        "₈": "8",
        "₉": "9",
        "₊": "+",
        "₋": "-",
        "₌": "=",
        "ₙ": "n",
        "ᵢ": "i",
        "ⱼ": "j",
    }
)

_UNICODE_TO_LATEX = {
    "×": r"\times ",
    "÷": r"\div ",
    "±": r"\pm ",
    "∓": r"\mp ",
    "≤": r"\le ",
    "≥": r"\ge ",
    "≠": r"\ne ",
    "≈": r"\approx ",
    "∞": r"\infty ",
    "→": r"\to ",
    "←": r"\leftarrow ",
    "↔": r"\leftrightarrow ",
    "∑": r"\sum ",
    "∏": r"\prod ",
    "∫": r"\int ",
    "∂": r"\partial ",
    "∇": r"\nabla ",
    "∈": r"\in ",
    "∉": r"\notin ",
    "⊂": r"\subset ",
    "⊆": r"\subseteq ",
    "∪": r"\cup ",
    "∩": r"\cap ",
    "α": r"\alpha ",
    "β": r"\beta ",
    "γ": r"\gamma ",
    "δ": r"\delta ",
    "ε": r"\epsilon ",
    "θ": r"\theta ",
    "λ": r"\lambda ",
    "μ": r"\mu ",
    "π": r"\pi ",
    "ρ": r"\rho ",
    "σ": r"\sigma ",
    "φ": r"\phi ",
    "χ": r"\chi ",
    "ω": r"\omega ",
    "Δ": r"\Delta ",
    "Σ": r"\Sigma ",
    "Π": r"\Pi ",
    "Ω": r"\Omega ",
}


def _strip_math_delimiters(source: str) -> tuple[str, list[str]]:
    repairs: list[str] = []
    text = source.strip()
    pairs = (("$$", "$$"), (r"\[", r"\]"), (r"\(", r"\)"), ("$", "$"))
    for left, right in pairs:
        if text.startswith(left) and text.endswith(right) and len(text) >= len(left) + len(right):
            text = text[len(left) : -len(right)].strip()
            break
    if "$" in text:
        text = re.sub(r"(?<!\\)\$+", "", text)
        repairs.append("removed misplaced dollar delimiters")
    return text, repairs


def _replace_script_run(text: str, characters: str, marker: str, table: dict[int, str]) -> str:
    pattern = re.compile(f"([{re.escape(characters)}]+)")
    return pattern.sub(lambda match: marker + "{" + match.group(0).translate(table) + "}", text)


def _fix_empty_environments(text: str, repairs: list[str]) -> str:
    if r"\begin{}" not in text and r"\end{}" not in text:
        return text
    environment = "cases" if "&" in text and re.search(r"\\text\s*\{\s*if\b", text) else "aligned"
    text = text.replace(r"\begin{}", rf"\begin{{{environment}}}")
    text = text.replace(r"\end{}", rf"\end{{{environment}}}")
    repairs.append(f"inferred missing {environment} environment name")
    return text


def _close_expectations_before_equals(text: str, repairs: list[str]) -> str:
    # Common copy/paste damage: E[(... )^2$$= ...
    pattern = re.compile(r"(E\s*\[[^\]]{1,240}?)(\s*=\s*(?:\\begin|E\s*\[))")
    updated, count = pattern.subn(r"\1]\2", text)
    if count:
        repairs.append("closed an incomplete expectation bracket")
    return updated


def _repair_unmatched_brackets(text: str, repairs: list[str]) -> str:
    # Mixed delimiters are intentional in half-open interval notation: [a,b) or (a,b].
    if re.fullmatch(r"\s*[\[(][^,\n]{1,120},[^,\n]{1,120}[\])]\s*", text):
        return text
    pairs = {")": "(", "]": "["}
    opens = set(pairs.values())
    stack: list[tuple[str, int]] = []
    remove: set[int] = set()
    escaped = False
    in_text_command = 0
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{" and text[max(0, index - 6) : index] == r"\text":
            in_text_command += 1
            continue
        if char == "}" and in_text_command:
            in_text_command -= 1
            continue
        if in_text_command:
            continue
        if char in opens:
            stack.append((char, index))
        elif char in pairs:
            if stack and stack[-1][0] == pairs[char]:
                stack.pop()
            else:
                remove.add(index)
    if remove:
        # A trailing unmatched ']' after a numeric annotation usually lost its opener.
        if len(remove) == 1:
            index = next(iter(remove))
            if text[index] == "]":
                tail = text[max(0, index - 40) : index]
                match = re.search(r"(?:^|\s)([0-9][0-9.,\\%\s]+)$", tail)
                if match:
                    insertion = max(0, index - len(match.group(1)))
                    text = text[:insertion] + "[" + text[insertion:]
                    repairs.append("restored a missing opening bracket")
                    return text
        text = "".join(char for i, char in enumerate(text) if i not in remove)
        repairs.append("removed unmatched closing bracket")
    if stack:
        closers = {"(": ")", "[": "]"}
        text += "".join(closers[item[0]] for item in reversed(stack))
        repairs.append("closed unmatched bracket")
    return text


def _repair_braces(text: str, repairs: list[str]) -> str:
    depth = 0
    escaped = False
    remove: set[int] = set()
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
            else:
                remove.add(index)
    if remove:
        text = "".join(char for i, char in enumerate(text) if i not in remove)
        repairs.append("removed unmatched closing brace")
    if depth:
        text += "}" * depth
        repairs.append("closed unmatched brace")
    return text


def _normalize_plain_math(text: str, repairs: list[str]) -> str:
    original = text
    supers = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼ⁿ"
    subs = "₀₁₂₃₄₅₆₇₈₉₊₋₌ₙᵢⱼ"
    text = _replace_script_run(text, supers, "^", _SUPERSCRIPTS)
    text = _replace_script_run(text, subs, "_", _SUBSCRIPTS)
    text = re.sub(r"√\s*\(([^()]*)\)", r"\\sqrt{\1}", text)
    text = re.sub(r"√\s*([A-Za-z0-9]+)", r"\\sqrt{\1}", text)
    for symbol, latex in _UNICODE_TO_LATEX.items():
        text = text.replace(symbol, latex)
    if text != original:
        repairs.append("normalized UnicodeMath symbols")
    return text


def repair_formula(source: str, *, plain_math: bool = False) -> tuple[str, list[str]]:
    """Return Pandoc-compatible TeX plus an auditable list of conservative repairs."""
    # NFC keeps semantic superscript/subscript code points intact for the conversion below.
    text, repairs = _strip_math_delimiters(unicodedata.normalize("NFC", source))
    text = text.replace("＼", "\\").replace("﹨", "\\")
    text = text.replace("\u00a0", " ").replace("\u200e", "").replace("\u200f", "")
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = _fix_empty_environments(text, repairs)
    text = _close_expectations_before_equals(text, repairs)
    if plain_math or re.search(r"[√∑∫≤≥≠≈∞→←↔α-ωΑ-Ω⁰-⁹₀-₉]", text):
        text = _normalize_plain_math(text, repairs)
    text = _repair_unmatched_brackets(text, repairs)
    text = _repair_braces(text, repairs)
    text = re.sub(r"\\(begin|end)\s*\{\s*\}", r"\\\1{aligned}", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text, list(dict.fromkeys(repairs))
