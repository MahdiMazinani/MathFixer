# MathFixer beginner guide

1. Download `MathFixer-Windows-Portable.zip` from the latest GitHub Release.
2. Extract the ZIP. Do not run the EXE from inside the ZIP preview.
3. Double-click `MathFixer.exe`.
4. Drop a `.docx`, `.docm`, or `.tex` document into the large selection area.
5. Keep **Balanced** mode unless you want explicit delimiters only (**Safe**) or broader detection (**Aggressive**).
6. Keep AI at **Off — recommended** and thesis compatibility at **Off — no university template** unless you intentionally need them.
7. Choose optional outputs: PDF, Word→LaTeX, and HTML/JSON report.
8. Select **Scan & repair files** once. The original remains unchanged.
9. Select **Change report** to inspect every automatic modification, **Review selected** for details, or **Open output** to open its folder.

AI diagnostics are optional and explicitly off by default. Selecting a provider sends TEX text to that provider and can wait up to 90 seconds; do not enable AI for confidential work unless permitted.

If atomic conversion fails, wait while MathFixer automatically prepares review data. Then choose **Review selected**, disable or correct the unwanted candidate, and run the single action again. Optional PDF engines each have a 45-second GUI limit; PDF failure keeps the validated Word output and marks it with a warning.

The document row shows the current Word stage. **Converting formulas with Pandoc** normally completes in seconds and has a 45-second total limit in version 2.0.3. If an older version remains there for minutes, close it, install the latest Release, and retry; the source file is never modified. A document with no detected formulas skips Pandoc.

For DOCM files, PDF export requires desktop Microsoft Word so VBA can be force-disabled. For TEX-to-PDF, XeLaTeX must be installed separately.
