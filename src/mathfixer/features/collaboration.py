from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .ai_providers import _open_without_redirect, _validated_endpoint


@dataclass(frozen=True, slots=True)
class ReviewBundle:
    path: str
    files: tuple[str, ...]
    includes_sources: bool


def create_review_bundle(
    report_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    *,
    source_paths: list[str | os.PathLike[str]] | None = None,
    include_sources: bool = False,
) -> ReviewBundle:
    report = Path(report_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if report.suffix.lower() != ".json" or not report.is_file():
        raise ValueError("A review bundle requires an existing JSON MathFixer report.")
    if target.suffix.lower() != ".mfxreview":
        raise ValueError("Review bundle output must use the .mfxreview extension.")
    raw = report.read_bytes()
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError("Report is too large for a collaboration bundle.")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("MathFixer report must contain a JSON object.")
    for key in ("input_path", "output_path", "pdf_path"):
        value = parsed.get(key)
        if isinstance(value, str) and value:
            parsed[key] = Path(value).name
    sanitized_report = json.dumps(parsed, ensure_ascii=False, indent=2).encode("utf-8")
    sources = [Path(path).expanduser().resolve() for path in (source_paths or [])]
    if sources and not include_sources:
        raise ValueError("Source files require explicit include_sources=True consent.")
    if len(sources) > 20:
        raise ValueError("A review bundle can include at most 20 explicitly selected source files.")
    for source in sources:
        if not source.is_file() or source.stat().st_size > 64 * 1024 * 1024:
            raise ValueError(f"Invalid or oversized collaboration source: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": "mathfixer-review",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "includes_sources": bool(sources),
        "source_count": len(sources),
    }
    names = ["manifest.json", "report.json"]
    with tempfile.NamedTemporaryFile(
        prefix=f".{target.stem}-", suffix=target.suffix, dir=target.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            archive.writestr("report.json", sanitized_report)
            for index, source in enumerate(sources, 1):
                name = f"sources/{index:02d}-{source.name}"
                archive.write(source, name)
                names.append(name)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return ReviewBundle(str(target), tuple(names), bool(sources))


def upload_review_bundle(
    bundle_path: str | os.PathLike[str],
    endpoint: str,
    *,
    token: str = "",
    timeout: int = 120,
) -> dict:
    bundle = Path(bundle_path).expanduser().resolve()
    if bundle.suffix.lower() != ".mfxreview" or not bundle.is_file():
        raise ValueError("Upload requires an existing .mfxreview bundle.")
    if bundle.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("Review bundle exceeds the upload safety limit.")
    headers = {"Content-Type": "application/vnd.mathfixer.review+zip"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        _validated_endpoint(endpoint),
        data=bundle.read_bytes(),
        headers=headers,
        method="POST",
    )
    try:
        with _open_without_redirect(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Collaboration upload failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Collaboration service returned invalid JSON.")
    return payload
