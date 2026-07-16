# Contributing

Contributions are welcome, especially anonymized minimal DOCX fixtures that expose a new equation-damage pattern.

1. Open an issue describing the source notation, expected formula, detection mode, and Word version.
2. Never commit private documents. Reduce a reproducer to the smallest synthetic file.
3. Add a detector/repair unit test and, when Pandoc is involved, a preservation integration test.
4. Run `python -m unittest discover -s tests -v`, `python -m compileall -q src`, and `ruff check .`.
5. Keep repairs conservative and auditable. A lower-confidence candidate that can be reviewed is better than silently changing prose.

Pull requests should explain whether they affect detection, mathematical normalization, OOXML mutation, or preservation auditing.
