from __future__ import annotations

import html
import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _atomic_text_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=f".{path.stem}-", suffix=path.suffix,
        dir=path.parent, delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_report(path: Path, data: dict[str, Any]) -> None:
    _atomic_text_write(path, json.dumps(data, ensure_ascii=False, indent=2))


def _change_rows(candidates: Iterable[dict[str, Any]]) -> str:
    rows: list[str] = []
    for item in candidates:
        repairs = item.get("repairs") or []
        reason = "; ".join(str(value) for value in repairs) or "Converted to native Office Math"
        if not item.get("enabled", True):
            reason = "Skipped by user"
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(str(item.get('source', '')))}</code></td>"
            f"<td><code>{html.escape(str(item.get('normalized', '')))}</code></td>"
            f"<td>{html.escape(reason)}</td>"
            f"<td>{html.escape(str(item.get('part', '')))} · {int(item.get('paragraph_index', 0)) + 1}</td>"
            "</tr>"
        )
    return "".join(rows) or '<tr><td colspan="4">No changes were required.</td></tr>'


def write_html_report(path: Path, report: dict[str, Any], *, language: str = "en") -> None:
    rtl = language == "fa"
    title = "گزارش اصلاحات MathFixer" if rtl else "MathFixer repair report"
    labels = (
        ("قبل", "بعد", "دلیل", "محل", "یافت‌شده", "تبدیل‌شده", "ردشده")
        if rtl else
        ("Before", "After", "Reason", "Location", "Detected", "Converted", "Skipped")
    )
    before, after, reason, location, detected, converted, skipped = labels
    document = html.escape(Path(str(report.get("input_path", ""))).name)
    body = f"""<!doctype html>
<html lang="{'fa' if rtl else 'en'}" dir="{'rtl' if rtl else 'ltr'}">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:Segoe UI,Tahoma,sans-serif;margin:0;background:#f4f7fb;color:#172033}}
main{{max-width:1100px;margin:36px auto;padding:0 20px}}h1{{margin-bottom:4px}}.muted{{color:#607086}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0}}.card{{background:white;border:1px solid #d9e2ec;border-radius:14px;padding:18px}}
.value{{font-size:28px;font-weight:750;color:#195cc7}}table{{width:100%;border-collapse:collapse;background:white;border-radius:14px;overflow:hidden}}
th,td{{padding:13px;text-align:{'right' if rtl else 'left'};border-bottom:1px solid #e5eaf0;vertical-align:top}}th{{background:#eaf2fb}}code{{white-space:pre-wrap;word-break:break-word;color:#7c2d12}}
@media(max-width:700px){{.cards{{grid-template-columns:1fr}}table{{font-size:13px}}}}
</style><main><h1>{title}</h1><div class="muted">{document}</div>
<section class="cards"><div class="card"><div class="value">{report.get('detected', 0)}</div>{detected}</div>
<div class="card"><div class="value">{report.get('converted', 0)}</div>{converted}</div>
<div class="card"><div class="value">{report.get('skipped', 0)}</div>{skipped}</div></section>
<table><thead><tr><th>{before}</th><th>{after}</th><th>{reason}</th><th>{location}</th></tr></thead>
<tbody>{_change_rows(report.get('candidates', []))}</tbody></table></main></html>"""
    _atomic_text_write(path, body)
