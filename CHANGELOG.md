# Changelog

## 2.0.4 — 2026-07-18

- Fixed every retry being reported as failed when the intended output filename already existed.
- When replacement is off, automatically selects a safe numbered sibling such as `_mathfixed_2.docx`; existing DOCX, PDF, reports and TEX outputs remain untouched.
- Applied the same non-conflicting naming policy to complete LaTeX project output directories.
- Displayed a localized, readable failure reason directly in the queue and final summary instead of hiding the technical exception only in a tooltip.
- Expanded the real Windows GUI conversion test to begin with an occupied output name and verify that it publishes the numbered output without replacing the existing file.

## 2.0.3 — 2026-07-18

- Fixed the remaining Word conversion hang when AI, thesis mode, PDF and atomic mode are all off.
- Replaced Pandoc pipe-based execution with file-backed output and deterministic child-tree cleanup.
- Added a 30-second per-batch and 45-second whole-document Pandoc limit; a timed-out batch is never retried for every remaining formula group.
- Retained Qt workers until all completion/error signals are delivered, preventing frozen Windows builds from losing a result callback.
- Skipped Pandoc entirely for documents with no detected formulas.
- Displayed the current localized processing stage directly in each queue row.
- Added real DOCX conversion through the Windows GUI worker and a post-build frozen-EXE/embedded-Pandoc smoke test.

## 2.0.2 — 2026-07-18

- Fixed the apparent conversion hang caused by optional PDF engines waiting up to six minutes.
- Limited each GUI PDF engine to 45 seconds and terminated its child process tree on timeout.
- Preserved the validated Word output when optional PDF generation fails and surfaced a visible warning.
- Added automatic recovery scanning after conversion errors so Review selected works without a separate scan action.
- Replaced the obsolete Scan first message with processing/recovery guidance and added per-file progress percentages.
- Added Windows GUI recovery smoke coverage and PDF timeout/nonfatal-output regression tests.

## 2.0.1 — 2026-07-18

- Replaced the confusing two-button desktop scan/convert flow with one **Scan & repair files** action.
- Added explicit **Off — recommended** AI selection and **Off — no university template** thesis selection.
- Avoided the redundant Word pre-scan in the default one-click path.
- Added visible operation details and the 90-second AI wait limit to the progress status.
- Updated English/Persian README files, beginner guides, quick help and the UI preview for the new workflow.

## 2.0.0 — 2026-07-17

- Added the stable public Python API v2 and read-only diagnostics Plugin SDK.
- Added isolated third-party plugin discovery with API-major compatibility checks and failure containment.
- Added bidirectional Word↔LaTeX project conversion with extracted media, resource paths, optional reference DOCX, staging and output validation.
- Added OpenAI Responses, OpenAI-compatible private endpoint and local Ollama provider adapters; AI remains explicit and advisory.
- Added offline `.mfxreview` collaboration bundles that exclude source files by default and an opt-in private-service upload boundary.
- Added complete-project LaTeX repair that copies the project before changing included sources.
- Expanded the desktop app with provider selection, complete-project mode, exact multi-file locations and PDF comparison.
- Replaced the misleading single-fraction graphic with a complex scientific-document workflow illustration.
- Rebuilt the English and Persian README files as full product, GUI, CLI, API, plugin, security and troubleshooting manuals.

## 1.3.0 — 2026-07-17

- Added bounded multi-file LaTeX workspace indexing for `input`, `include` and `subfile` sources.
- Added project-wide citation/reference checks, duplicate-label detection and exact relative file/line evidence.
- Improved TeX log parsing with nested-file and file-line-error locations.
- Added safe JSON template adapters for licensed or user-provided university templates.
- Added rendered PDF comparison with page geometry checks, pixel metrics, heatmaps and JSON regression output.
- Added an Inno Setup installer workflow and optional Authenticode signing path when a certificate is configured.
- Added diagnostics to readable HTML reports instead of exposing them only in JSON.

## 1.2.0 — 2026-07-16

- Repositioned MathFixer as a formula repair and scientific document assistant.
- Added TEX scanning and conservative fraction repair with HTML before/after reports.
- Added Persian font, xepersian, bidi and local BibTeX citation diagnostics.
- Added optional OpenAI diagnostics and explicit Word-to-LaTeX export.
- Added thesis compatibility profiles and a product-focused desktop dashboard.
- Added secure XML parsing, duplicate/encrypted ZIP rejection and native-math delta validation.
- Force-disabled Word macros for DOCM PDF and prohibited unverified LibreOffice DOCM export.
- Added proper block-level OMML for equation-only display formulas.
- Expanded CI across Windows/Linux and Python 3.10–3.12 with GUI smoke, CodeQL and Dependabot.
- Added tagged automated releases with SHA-256 checksums.

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
