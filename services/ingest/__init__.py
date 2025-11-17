"""
Document ingestion service for PDFs and text files.
Extracts text with byte-level offsets for citation tracking.
"""

from .pdf_parser import PDFParser, ParsedDocument, TextSpan

__all__ = [
    "PDFParser",
    "ParsedDocument",
    "TextSpan",
]
