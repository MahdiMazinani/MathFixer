# Security policy

Please report document-parsing vulnerabilities privately through GitHub's security advisory feature.

MathFixer treats DOCX/DOCM files as untrusted ZIP packages. It imposes member, expanded-size and compression-ratio limits; rejects duplicate and encrypted entries; disables XML DTD/entity/network resolution; and never extracts arbitrary member paths to disk. The original file is never overwritten.

DOCM-to-PDF is permitted only through Microsoft Word on Windows. Word automation sets `AutomationSecurityForceDisable` before opening the document. LibreOffice is not used as a DOCM fallback because its effective macro policy can vary by installation.

Optional AI analysis is off by default. When explicitly enabled, document source is sent to the configured API. API keys are read from environment variables and are not persisted by MathFixer. Users must not enable remote analysis for confidential documents unless their data policy permits it.

LaTeX workspace discovery reads only relative TEX/BibTeX paths that resolve inside the selected project root and enforces source-count and total-size limits. Unsafe traversal, absolute includes and missing files become diagnostics.

Third-party Python plugins are code and must be installed only from trusted publishers. The SDK exposes a read-only diagnostics contract, validates API-major compatibility, and contains plugin exceptions, but it is not a process sandbox. University template adapter JSON is data-only and path-restricted.

Offline review bundles exclude source documents by default. Including a source requires explicit caller consent. Uploading a bundle is also explicit and targets only a user-configured HTTPS endpoint or local/private HTTP service. MathFixer does not operate a mandatory cloud backend.

PDF comparison renders untrusted PDFs through PDFium. Deployments that accept public uploads should additionally isolate the process, cap worker time/memory and keep PDFium current.

Supported security fixes target the latest minor release.
