# Architecture

MathFixer 2.0 separates stable document services from optional product features. Existing public imports remain compatible while API v2 exposes project-level workflows.

```text
mathfixer/
├── core/
│   ├── security.py          hardened OOXML/XML input boundary
│   └── reporting.py         atomic JSON and readable HTML reports
├── features/
│   ├── latex_project.py     TEX analysis, repair and XeLaTeX output
│   ├── latex_workspace.py   bounded include graph and cross-file evidence
│   ├── project_conversion.py media-aware Word↔LaTeX project conversion
│   ├── pdf_compare.py       rendered page regression and heatmaps
│   ├── collaboration.py     offline review bundle and opt-in upload boundary
│   ├── citations.py         local BibTeX key validation
│   ├── persian.py           xepersian/font/bidi diagnostics
│   ├── word_to_latex.py     explicit Pandoc export
│   ├── ai_providers.py      OpenAI/private/Ollama provider adapters
│   └── ai_assistant.py      structured advisory findings
├── plugins/
│   ├── sdk.py               stable read-only diagnostics Plugin API
│   ├── template_adapter.py  safe data-only template requirements
│   └── thesis.py            university compatibility profile registry
├── api.py                   public Python API v2
├── detector.py              Word formula candidate detection
├── repair.py                conservative deterministic normalization
├── pandoc_backend.py        isolated math-fragment compiler
├── docx_engine.py           OOXML scan, patch and preservation audit
├── pdf_export.py            macro-safe Word/LibreOffice PDF boundary
├── gui.py                   desktop orchestration and presentation
└── cli.py                   automation interface
```

## Trust boundaries

1. Input files are untrusted. ZIP limits and a no-DTD/no-entity/no-network XML parser run before document processing.
2. Deterministic repair is the default. Ambiguous changes become findings for human review.
3. Pandoc receives isolated formula strings for Word repair; it never rebuilds the source Word document.
4. DOCM PDF export uses Word only and sets `AutomationSecurityForceDisable` before opening the file.
5. AI is optional, advisory and explicit. The desktop application does not persist credentials.
6. Output documents are published through atomic replacement only after package validation. Reports are written atomically and reporting failure is recorded without corrupting a valid document.
7. LaTeX includes are resolved only inside a bounded project root; absolute/traversal paths are findings, not reads.
8. Collaboration bundles exclude sources unless the caller provides explicit per-command consent.
9. Remote AI/collaboration endpoints require HTTPS; local/private hosts may use HTTP for on-device services.

## Plugin direction

The Python Plugin SDK uses the `mathfixer.plugins` entry-point group and API-major compatibility checks. Plugins receive an immutable context and return diagnostics; no source-writing interface is exposed. Data-only template adapters are preferred for institutional requirements. University-specific support requires a user-provided or appropriately licensed template plus regression fixtures; a profile name alone does not imply official endorsement.

## Output contracts

- Word repair: output package entry set is preserved, unmodified parts remain byte-identical and the native-math delta must equal successful conversions.
- LaTeX repair: only narrowly defined deterministic replacements are applied to a different output path.
- LaTeX project repair: the project is copied to a sibling staging directory before included sources are changed.
- Reports: every applied repair includes before, after, reason and location.
- PDF: output must have a PDF header, EOF marker and a valid page count when `pypdf` is available.
- Visual comparison: every page has geometry, changed-pixel ratio and an auditable heatmap.
