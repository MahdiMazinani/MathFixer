"""Academic references and template compatibility plugin boundary."""

from ..features.citations import find_missing_citations, find_missing_references
from .thesis import THESIS_PROFILES, ThesisProfile

__all__ = [
    "THESIS_PROFILES",
    "ThesisProfile",
    "find_missing_citations",
    "find_missing_references",
]
