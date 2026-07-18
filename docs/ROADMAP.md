# MathFixer roadmap

## v1.0 — Word formula engine

- Layout-preserving OOXML patching
- Native Office Math conversion
- GUI, batch processing and audit JSON

## v1.1 — Accessible desktop release

- Persian/English interface
- Light and dark themes
- Portable Windows EXE with Pandoc
- Word/PDF output

## v1.2 — Scientific document assistant

- Clear product identity and beginner-first interface
- DOCX, DOCM and TEX input
- Side-by-side HTML change reports
- Persian font, bidi, XeLaTeX and citation diagnostics
- Word→LaTeX export
- Optional OpenAI diagnostics with explicit consent
- Thesis compatibility profile registry
- Hardened XML/ZIP and macro-safe DOCM PDF export
- Windows/Linux CI, GUI smoke test, CodeQL, Dependabot and release checksums

## v1.3 — Evidence-based thesis plugins — completed

- Data-only adapters for licensed or user-provided university templates
- Reference/citation/duplicate-label cross-checking across multi-file LaTeX projects
- Compilation-log parser with exact nested file and line locations
- Rendered visual PDF comparison, heatmaps and regression metrics
- Windows installer plus Authenticode signing when a certificate is configured

## v2.0 — Extensible document platform — completed

- Stable read-only diagnostics Plugin SDK and public Python API v2
- Project-wide Word↔LaTeX conversion with media handling and validation
- OpenAI, OpenAI-compatible private and Ollama provider adapters
- Offline review bundles and an opt-in user-configured collaboration-service boundary

## After v2.0

- Expand deterministic repair rules only when regression fixtures prove safety.
- Add officially licensed institutional adapters when maintainers receive redistribution permission.
- Sign public installers after a project-controlled Authenticode certificate is available.
- Keep local/offline workflows fully functional as optional integrations grow.

Completed means implemented and covered by repository tests. A public version is released only after its tagged build artifacts pass CI. External assets such as university templates, signing certificates and collaboration backends are never implied by an integration boundary.
