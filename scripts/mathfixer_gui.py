from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _bundled_self_test(input_path: Path, output_path: Path) -> int:
    """CI entry point that proves the frozen EXE can run its embedded Pandoc."""
    try:
        from mathfixer.docx_engine import convert_document

        report = convert_document(
            input_path,
            output_path,
            overwrite=True,
            fail_on_formula_error=False,
            create_pdf=False,
            pandoc_timeout=15,
            pandoc_total_timeout=20,
        )
        if not report.success or not output_path.is_file():
            raise RuntimeError("The bundled conversion did not publish a validated DOCX output.")
        return 0
    except Exception:
        output_path.with_suffix(".error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        return 2


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--self-test":
        return _bundled_self_test(Path(sys.argv[2]), Path(sys.argv[3]))
    from mathfixer.gui import run

    return run()

if __name__ == "__main__":
    raise SystemExit(main())
