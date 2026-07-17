# Security policy

Please report document-parsing vulnerabilities privately through GitHub's security advisory feature.

MathFixer treats DOCX/DOCM files as untrusted ZIP packages. It imposes member, expanded-size and compression-ratio limits; rejects duplicate and encrypted entries; disables XML DTD/entity/network resolution; and never extracts arbitrary member paths to disk. The original file is never overwritten.

DOCM-to-PDF is permitted only through Microsoft Word on Windows. Word automation sets `AutomationSecurityForceDisable` before opening the document. LibreOffice is not used as a DOCM fallback because its effective macro policy can vary by installation.

Optional AI analysis is off by default. When explicitly enabled, document source is sent to the configured API. API keys are read from environment variables and are not persisted by MathFixer. Users must not enable remote analysis for confidential documents unless their data policy permits it.

Supported security fixes target the latest minor release.
