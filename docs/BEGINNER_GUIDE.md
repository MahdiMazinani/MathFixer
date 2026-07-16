# MathFixer beginner guide

The ready-made Windows build requires no programming knowledge.

1. Open the repository's latest **Release**.
2. Under **Assets**, download `MathFixer-Windows-Portable.zip`.
3. Extract the ZIP and double-click `MathFixer.exe`.
4. Drop one or more DOCX/DOCM files into the window.
5. Keep **Balanced** mode and choose **Scan & review**.
6. Review candidates if desired, enable PDF if needed, then choose **Convert all**.

The original document is never overwritten. Outputs use the `_mathfixed` suffix.
The portable build already contains Python dependencies and Pandoc. Optional PDF
creation needs desktop Microsoft Word or LibreOffice on the computer.

The language and dark/light theme selectors are at the top of the window. Both
preferences persist between launches.

If Windows SmartScreen appears, first verify that the file came from the official
repository Release. Early community builds may not yet have a commercial code-signing certificate.

All document processing is local; MathFixer does not upload documents to a conversion service.
