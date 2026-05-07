"""
Data ingestion module for Veg-Vibe.

Handles high-fidelity document parsing using Docling with
table-aware chunking and metadata preservation.

Modules:
- docling_parser: Core document parsing with Docling
- vectordb_compat: Vector database compatibility layer
- unified_ingestion: Unified URL ingestion for PDFs and menus
"""

from app.ingestion.docling_parser import (
    DocumentProcessor,
    ChunkedDocument,
    TableAwareChunk,
    get_document_processor,
)
from app.ingestion.vectordb_compat import (
    VectorDBFormatter,
    RAGCitationBuilder,
)
from app.ingestion.unified_ingestion import (
    NON_VEGAN_KEYWORDS,
    UnifiedIngestionTool,
    IngestionPayload,
    filter_vegan_text,
    ingest_source,
    parse_pdf_url,
    scrape_menu,
)

__all__ = [
    "DocumentProcessor",
    "ChunkedDocument",
    "TableAwareChunk",
    "get_document_processor",
    "VectorDBFormatter",
    "RAGCitationBuilder",
    "NON_VEGAN_KEYWORDS",
    "UnifiedIngestionTool",
    "IngestionPayload",
    "filter_vegan_text",
    "ingest_source",
    "parse_pdf_url",
    "scrape_menu",
]
