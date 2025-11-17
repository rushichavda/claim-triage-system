"""
PDF parsing with byte-level offset tracking for citations.
Uses PyMuPDF (fitz) for accurate text extraction with positions.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import fitz  # PyMuPDF
from pydantic import BaseModel

from services.shared.schemas.citation import SourceDocument
from services.shared.utils import get_logger

logger = get_logger(__name__)


@dataclass
class TextSpan:
    """Text span with byte-level position tracking."""

    text: str
    start_byte: int
    end_byte: int
    page_number: int
    paragraph_index: int


class ParsedDocument(BaseModel):
    """Result of PDF parsing with text and metadata."""

    document_id: UUID
    source_path: str
    total_pages: int
    total_bytes: int
    content_hash: str
    full_text: str
    spans: list[TextSpan]  # Text spans with positions


class PDFParser:
    """
    PDF parser with byte-level offset tracking.
    Critical for creating verifiable citations.
    """

    def __init__(self) -> None:
        self.logger = logger.bind(component="PDFParser")

    def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        """
        Parse a PDF file and extract text with byte offsets.

        Args:
            pdf_path: Path to PDF file

        Returns:
            ParsedDocument with text and span information

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF cannot be parsed
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        self.logger.info("parsing_pdf", pdf_path=str(pdf_path))

        try:
            doc = fitz.open(pdf_path)
            spans: list[TextSpan] = []
            full_text_parts: list[str] = []
            current_byte_offset = 0
            total_pages = len(doc)  # Capture page count before closing

            for page_num in range(total_pages):
                page = doc[page_num]
                page_text = page.get_text("text")

                # Split into paragraphs (double newline or significant spacing)
                paragraphs = self._split_into_paragraphs(page_text)

                for para_idx, para_text in enumerate(paragraphs):
                    if not para_text.strip():
                        continue

                    # Calculate byte positions
                    para_bytes = para_text.encode("utf-8")
                    start_byte = current_byte_offset
                    end_byte = start_byte + len(para_bytes)

                    span = TextSpan(
                        text=para_text,
                        start_byte=start_byte,
                        end_byte=end_byte,
                        page_number=page_num + 1,  # 1-indexed
                        paragraph_index=para_idx,
                    )
                    spans.append(span)
                    full_text_parts.append(para_text)

                    current_byte_offset = end_byte

            doc.close()

            # Combine full text
            full_text = "\n\n".join(full_text_parts)
            full_text_bytes = full_text.encode("utf-8")

            # Calculate content hash
            content_hash = hashlib.sha256(full_text_bytes).hexdigest()

            document_id = uuid4()

            self.logger.info(
                "pdf_parsed",
                document_id=str(document_id),
                pages=total_pages,
                spans=len(spans),
                total_bytes=len(full_text_bytes),
            )

            return ParsedDocument(
                document_id=document_id,
                source_path=str(pdf_path),
                total_pages=total_pages,
                total_bytes=len(full_text_bytes),
                content_hash=content_hash,
                full_text=full_text,
                spans=spans,
            )

        except Exception as e:
            self.logger.error("pdf_parse_error", pdf_path=str(pdf_path), error=str(e))
            raise ValueError(f"Failed to parse PDF: {e}") from e

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """
        Split text into paragraphs.
        Simple implementation - can be enhanced with NLP.
        """
        # Split by double newlines first
        paragraphs = text.split("\n\n")

        # Further split long single paragraphs by single newlines if needed
        result = []
        for para in paragraphs:
            if len(para) > 1000:  # Long paragraph
                # Split by single newlines
                sub_paras = para.split("\n")
                result.extend([p for p in sub_paras if p.strip()])
            else:
                if para.strip():
                    result.append(para)

        return result

    def find_text_span(
        self, parsed_doc: ParsedDocument, search_text: str, fuzzy: bool = False
    ) -> Optional[TextSpan]:
        """
        Find a text span in the parsed document.

        Args:
            parsed_doc: Parsed document
            search_text: Text to search for
            fuzzy: Whether to use fuzzy matching

        Returns:
            TextSpan if found, None otherwise
        """
        search_text_clean = search_text.strip().lower()

        for span in parsed_doc.spans:
            span_text_clean = span.text.strip().lower()

            if fuzzy:
                # Simple fuzzy matching - can be enhanced
                if search_text_clean in span_text_clean or span_text_clean in search_text_clean:
                    return span
            else:
                if search_text_clean == span_text_clean:
                    return span

        return None

    def extract_span_by_byte_range(
        self, parsed_doc: ParsedDocument, start_byte: int, end_byte: int
    ) -> Optional[str]:
        """
        Extract text from a byte range.

        Args:
            parsed_doc: Parsed document
            start_byte: Start byte offset
            end_byte: End byte offset

        Returns:
            Extracted text or None
        """
        try:
            full_text_bytes = parsed_doc.full_text.encode("utf-8")
            span_bytes = full_text_bytes[start_byte:end_byte]
            return span_bytes.decode("utf-8")
        except Exception as e:
            self.logger.error(
                "byte_range_extraction_error",
                start_byte=start_byte,
                end_byte=end_byte,
                error=str(e),
            )
            return None

    def create_source_document(self, parsed_doc: ParsedDocument, doc_type: str, doc_name: str) -> SourceDocument:
        """
        Create a SourceDocument schema from parsed document.

        Args:
            parsed_doc: Parsed document
            doc_type: Type of document
            doc_name: Human-readable name

        Returns:
            SourceDocument instance
        """
        return SourceDocument(
            document_id=parsed_doc.document_id,
            document_type=doc_type,
            document_path=parsed_doc.source_path,
            document_name=doc_name,
            total_bytes=parsed_doc.total_bytes,
            total_pages=parsed_doc.total_pages,
            content_hash=parsed_doc.content_hash,
        )
