from .api import API_VERSION, repair, scan
from .docx_engine import ConversionAbortedError, convert_document, scan_document
from .models import ConversionReport, DetectionMode, FormulaCandidate, FormulaKind
from .pdf_export import PdfExportError, PdfExportResult, export_docx_to_pdf

__all__ = [
    "ConversionAbortedError",
    "API_VERSION",
    "ConversionReport",
    "DetectionMode",
    "FormulaCandidate",
    "FormulaKind",
    "PdfExportError",
    "PdfExportResult",
    "convert_document",
    "export_docx_to_pdf",
    "repair",
    "scan",
    "scan_document",
]

__version__ = "2.0.2"
