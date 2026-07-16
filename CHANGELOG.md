# Changelog

## 1.1.0 — 2026-07-16

- Added complete Persian/English interface switching with right-to-left Persian layout.
- Added persistent dark and light themes.
- Added optional validated PDF output through Microsoft Word or LibreOffice.
- Added beginner guides, quick in-app help, and a Windows portable Release workflow.
- Added PDF metadata/page reporting and CLI `--pdf`/`--pdf-engine` options.

## 1.0.3 — 2026-07-16

- Added frozen-app discovery for Pandoc bundled in PyInstaller's `_MEIPASS` directory.
- Updated the Windows build script to produce one self-contained EXE containing `pandoc.exe`.
- Added third-party redistribution notices.

## 1.0.2 — 2026-07-16

- Fixed detection-mode startup on PySide 6.11, which serializes string-based Enum values as plain QVariant strings.

## 1.0.1 — 2026-07-16

- Replaced the full PySide6 meta-package with PySide6-Essentials; the unnecessary 168 MB Addons wheel is no longer downloaded.

## 1.0.0 — 2026-07-16

- Replaced whole-document Pandoc reconstruction with layout-preserving OOXML surgery.
- Added layered LaTeX, damaged-TeX, UnicodeMath, and plain-equation detection.
- Added conservative repair with per-formula audit history.
- Added batched TeX-to-OMML fragment compilation without `pypandoc`.
- Added modern PySide6 desktop UI, drag/drop, batch queue, review, opt-out, and formula editing.
- Added CLI scan, convert, doctor, JSON reports, atomic output, and preservation validation.
- Added DOCX/DOCM safety checks and tests.
