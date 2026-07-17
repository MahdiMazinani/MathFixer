"""Stable core services shared by the GUI, CLI, and future plugins."""

from .reporting import write_html_report
from .security import parse_xml, validate_ooxml_archive

__all__ = ["parse_xml", "validate_ooxml_archive", "write_html_report"]
