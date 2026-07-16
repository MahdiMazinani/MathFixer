# MathFixer

**Repair broken LaTeX, UnicodeMath, and plain equations in Microsoft Word as native Office Math — without rebuilding the document.**

MathFixer is a desktop and command-line tool for documents in which formulas were pasted as `$...$`, split across Word runs, damaged by copy/paste, or written in linear Unicode notation. It converts only the formula fragments to native OMML. Every other OOXML package part is copied unchanged and audited before the output is published.

> The original document is never overwritten. Conversion is atomic by default: if one selected formula cannot be converted safely, no output is published.

[راهنمای فارسی](README_FA.md)

## Windows users - no programming required

Download `MathFixer-Windows-Portable.zip` from the repository's **latest
Release**, extract it, and double-click `MathFixer.exe`. Python and Pandoc are
already bundled. See the [beginner guide](docs/BEGINNER_GUIDE.md).

## Why MathFixer is different

Many Word/LaTeX scripts extract all paragraph text and ask Pandoc to create a new DOCX. That approach can lose styles, tables, images, headers, comments, tracked changes, fields, bookmarks, and section settings. MathFixer never sends the document to Pandoc. It uses Pandoc only as a TeX-to-OMML fragment compiler, then patches those OMML fragments into a copy of the original OOXML package.

| Capability | MathFixer |
|---|---|
| `$...$`, `$$...$$`, `\(...\)`, `\[...\]` | Yes |
| Raw TeX environments and common commands | Yes |
| Misplaced dollars, missing brackets, empty environments | Conservative auto-repair + audit trail |
| UnicodeMath (`σ²`, `√x`, `∑`, `≤`, `→`) | Yes |
| Strict equation-only text (`x = y + 1`) | Yes |
| Tables, text boxes, headers/footers, footnotes/endnotes, comments | Scanned in place |
| Existing native Word equations | Preserved and counted |
| DOCM macro packages | Package preserved; macros are never executed |
| Batch processing and drag/drop | Yes |
| Candidate preview, opt-out, manual normalization edit | Yes |
| JSON audit report | Yes |
| Persian and English interface | Yes |
| Dark and light themes | Yes |
| Optional PDF output | Microsoft Word or LibreOffice engine |
| Package integrity and structure audit | Mandatory |

## Install

MathFixer requires Python 3.10+ and [Pandoc](https://pandoc.org/installing.html). Pandoc is intentionally called as a subprocess; the fragile `pypandoc` download/runtime layer is not used.

```bash
git clone https://github.com/MahdiMazinani/MathFixer.git
cd MathFixer
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[gui]"
mathfixer doctor
mathfixer-gui
```

The GUI intentionally depends on `PySide6-Essentials`, not the full `PySide6`
meta-package. The much larger `PySide6-Addons` wheel is not required.

For command-line-only use:

```bash
pip install -e .
```

If Pandoc is installed in a non-standard location, set `MATHFIXER_PANDOC` or pass `--pandoc` in the CLI.

## Desktop workflow

1. Drop one or more `.docx`/`.docm` files into the app.
2. Choose a detection mode:
   - **Safe:** explicit math delimiters only.
   - **Balanced:** explicit, malformed/raw TeX, UnicodeMath, and strict equation-only lines. Recommended.
   - **Aggressive:** also considers short math-heavy lines without a clear equation boundary.
3. Select **Scan & review** to inspect confidence, repairs, and normalized TeX. Uncheck a false positive or edit a repair.
4. Select **Convert all**. The output and optional `.report.json` are written beside the source or into the selected output folder.
5. Enable **Also create a PDF** when a PDF copy is needed. On Windows, MathFixer uses desktop Microsoft Word first and LibreOffice as a fallback.

## CLI

```bash
# Dependency check
mathfixer doctor

# Read-only scan
mathfixer scan thesis.docx --mode balanced --json scan.json

# One file, with an audit report
mathfixer convert thesis.docx --report

# Create repaired DOCX and PDF together
mathfixer convert thesis.docx --pdf --report

# Batch conversion into a separate directory
mathfixer convert chapter*.docx -o fixed --suffix _native --report

# Keep successful formulas if another formula fails (atomic mode is the default)
mathfixer convert notes.docx --continue-on-error
```

## Preservation contract

Before publishing an output, MathFixer verifies:

- the DOCX ZIP is readable and every member passes a CRC test;
- the package entry set is identical;
- every unmodified OOXML/media part is byte-identical;
- table, drawing, legacy picture, hyperlink, bookmark, comment-range, tracked-change, and section counts are unchanged;
- ordinary paragraph text around every replaced formula is unchanged;
- only selected formulas became native `m:oMath` objects.

The JSON report includes every candidate, confidence score, repair action, warning, Pandoc version, modified story part, and preservation result.

## Detection and repair philosophy

Mathematical text is ambiguous: `$100` may be currency, `A-B` may be prose, and an equation can be embedded in a field or hyperlink. MathFixer therefore uses layered detection and confidence scoring, exposes candidates before conversion, and refuses unsafe run structures instead of flattening them. Repairs are deliberately narrow and recorded. It does not silently invent mathematical meaning.

Image-only equations are not OCR-converted in v1. OCR would be probabilistic and would conflict with the strict no-unreviewed-changes guarantee. They remain byte-identical in the output.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
ruff check .
```

See the [beginner guide](docs/BEGINNER_GUIDE.md), [Architecture](docs/ARCHITECTURE.md), [Contributing](CONTRIBUTING.md), and [Security](SECURITY.md).

## Build a self-contained Windows executable

The included PowerShell script detects the installed `pandoc.exe`, embeds it in
the PyInstaller one-file executable, and makes the frozen app discover the
temporary bundled binary automatically:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The result is `dist\MathFixer.exe`. A destination computer does not need Python,
MathFixer dependencies, or a separate Pandoc installation. Pandoc is distributed
under the GNU GPL; keep `THIRD_PARTY_NOTICES.md` with any distributed binary and
review its license obligations before publishing a release.

## License

MIT
