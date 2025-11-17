"""
Extractor agent - extracts structured claim data from denial documents.
Uses LLM with structured output (Instructor) for reliable extraction.
"""

from .extractor_agent import ExtractorAgent, ExtractionResult

__all__ = ["ExtractorAgent", "ExtractionResult"]
