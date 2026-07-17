# MathFixer beginner guide

1. Download `MathFixer-Windows-Portable.zip` from the latest GitHub Release.
2. Extract the ZIP. Do not run the EXE from inside the ZIP preview.
3. Double-click `MathFixer.exe`.
4. Drop a `.docx`, `.docm`, or `.tex` document into the large selection area.
5. Keep **Balanced** mode unless you want explicit delimiters only (**Safe**) or broader detection (**Aggressive**).
6. Select **Scan & review**. Review Before, After, Reason and Location; disable any unwanted Word formula candidate.
7. Choose optional outputs: PDF, Word→LaTeX, and HTML/JSON report.
8. Select **Start repair**. The original remains unchanged.
9. Select **Change report** to inspect every automatic modification, or **Open output** to open its folder.

AI diagnostics are optional and off by default. They send document text to the configured OpenAI API and require `OPENAI_API_KEY`; do not enable them for confidential work unless permitted.

For DOCM files, PDF export requires desktop Microsoft Word so VBA can be force-disabled. For TEX-to-PDF, XeLaTeX must be installed separately.
