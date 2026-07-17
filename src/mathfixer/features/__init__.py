"""Optional document-analysis features built on the stable MathFixer core."""

from .citations import find_missing_citations
from .persian import analyze_persian_latex
from .word_to_latex import export_word_to_latex

__all__ = ["analyze_persian_latex", "export_word_to_latex", "find_missing_citations"]
