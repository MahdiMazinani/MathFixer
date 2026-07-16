# Security policy

Please report document-parsing vulnerabilities privately through GitHub's security advisory feature.

MathFixer treats DOCX/DOCM files as untrusted ZIP packages. It imposes expanded-size and compression-ratio limits, never extracts arbitrary member paths to disk, never executes macros, and passes only isolated formula strings to Pandoc. The original file is never overwritten.

Supported security fixes target the latest minor release.
