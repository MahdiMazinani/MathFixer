# MathFixer

## Smart formula repair & scientific document assistant

**MathFixer repairs broken mathematical expressions in Word and LaTeX, explains every change, supports Persian thesis diagnostics, and can create validated PDF/LaTeX outputs.** It is built for students and researchers—not only programmers.

[راهنمای فارسی](README_FA.md) · [Download the latest Windows version](https://github.com/MahdiMazinani/MathFixer/releases/latest) · [Roadmap](docs/ROADMAP.md)

![MathFixer desktop interface](assets/app-preview.svg)

## See what changed

![Before and after formula repair](assets/before-after.svg)

Every automatic repair is recorded in a readable HTML report:

| Before | After | Reason |
|---|---|---|
| `\frac12` | `\frac{1}{2}` | Missing braces around fraction arguments |
| `frac12` | `\frac{1}{2}` | Missing command slash and braces |

## Windows: no programming required

1. Open the [latest Release](https://github.com/MahdiMazinani/MathFixer/releases/latest).
2. Download `MathFixer-Windows-Portable.zip`.
3. Extract the ZIP and double-click `MathFixer.exe`.
4. Drop a `.docx`, `.docm`, or `.tex` file into the app and select **Start repair**.

Python and Pandoc are bundled. Your original file is never overwritten. A SHA-256 checksum is included with every tagged release.

## What MathFixer does

- Repairs LaTeX delimiters, fractions, brackets and selected malformed environments.
- Converts LaTeX and UnicodeMath inside Word to native Office Math without rebuilding the document.
- Correctly emits block-level Office Math for equation-only display formulas.
- Analyzes `.tex` documents for missing packages, citations, braces, Persian fonts and bidi problems.
- Produces side-by-side HTML and machine-readable JSON change reports.
- Exports repaired documents to PDF and optionally converts Word to standalone LaTeX.
- Provides Persian/English UI, light/dark themes, batch processing and drag-and-drop.
- Offers optional AI diagnostics through OpenAI; it is off by default and requires the user’s own API key.

MathFixer does **not** silently rewrite academic prose, invent references, run document macros, or OCR image-only equations.

## Persian thesis mode

Persian documents receive additional checks for XeLaTeX-oriented workflows, `xepersian`, Persian/Latin font configuration, bidi environments and missing BibTeX keys. Compatibility profiles are included for user-supplied templates from Sharif, University of Tehran, Amirkabir, Tabriz and Islamic Azad University. These profiles are not official university templates or endorsements.

## Security and document preservation

- DOCX/DOCM is treated as an untrusted ZIP package.
- DTD loading, external XML entities and network access are disabled.
- Duplicate/encrypted entries, suspicious compression and oversized packages are rejected.
- DOCM-to-PDF is allowed only through Microsoft Word with VBA force-disabled.
- Unmodified package parts remain byte-identical.
- Table, drawing, relationship-sensitive structure and native-math deltas are audited before publishing output.
- AI analysis is opt-in. Source text is sent only after the user enables it; API keys are read from the environment and never saved.

See [Security](SECURITY.md) for reporting vulnerabilities.

## Optional AI diagnostics

AI analysis is explanatory and never applies changes by itself. Set credentials outside the application:

```powershell
$env:OPENAI_API_KEY="your-key"
$env:MATHFIXER_AI_MODEL="gpt-5-mini"  # optional override
```

Then enable **Optional AI diagnostics**. Do not enable it for confidential documents unless your data policy allows sending document text to the configured API.

## Developer installation

Ordinary Windows users do not need this section.

```bash
git clone https://github.com/MahdiMazinani/MathFixer.git
cd MathFixer
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[gui,dev]"
mathfixer doctor
mathfixer-gui
```

Pandoc is required for Word formula conversion and Word→LaTeX. XeLaTeX is required only when building PDF directly from a `.tex` file.

## CLI

```bash
mathfixer scan thesis.docx --mode balanced --json scan.json
mathfixer scan thesis.tex --json latex-scan.json
mathfixer convert thesis.docx --pdf --report
mathfixer convert thesis.tex --pdf --report
mathfixer word-to-latex thesis.docx thesis.tex
```

## Development quality gate

```bash
ruff check .
python -m compileall -q src
python -m unittest discover -s tests -v
```

CI runs on Windows and Linux with Python 3.10–3.12, includes a Windows GUI smoke test, CodeQL and Dependabot. Tagged releases build the portable EXE, publish checksums and use a narrowly scoped release permission.

## License

MathFixer is MIT-licensed. Bundled Pandoc remains GPL-2.0-or-later; distributors must follow [third-party notices](THIRD_PARTY_NOTICES.md).
