"""
Data ingestion module for Veg-Vibe.

Handles high-fidelity document parsing using Docling with
table-aware chunking and metadata preservation.

Modules:
- docling_parser: Core document parsing with Docling
- vectordb_compat: Vector database compatibility layer
- unified_ingestion: Unified URL ingestion for PDFs and menus
"""

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

try:
    # Prefer real types from docling_parser when available
    from app.ingestion.docling_parser import (
        DocumentProcessor,
        ChunkedDocument,
        TableAwareChunk,
        get_document_processor,
    )
except Exception:
    # Lightweight stubs for unit tests and runtime environments
    from dataclasses import dataclass, field
    from typing import Any, Dict, List, Optional


    @dataclass
    class TableAwareChunk:
        id: str
        content: str
        source_document: str
        page_number: int
        is_table: bool = False
        table_title: Optional[str] = None
        section_heading: Optional[str] = None
        metadata: Dict[str, Any] = field(default_factory=dict)
        confidence: float = 1.0

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "content": self.content,
                "source_document": self.source_document,
                "page_number": self.page_number,
                "is_table": self.is_table,
                "table_title": self.table_title,
                "section_heading": self.section_heading,
                "metadata": self.metadata,
                "confidence": self.confidence,
            }

        def to_embedding_text(self) -> str:
            return self.content

        def to_citation_reference(self) -> str:
            return f"{self.source_document}#page{self.page_number}:{self.id}"


    @dataclass
    class ChunkedDocument:
        source_path: str
        document_title: str
        total_pages: int
        chunks: List[TableAwareChunk]
        table_of_contents: Dict[str, Any]
        parsing_metadata: Dict[str, Any]

        def to_dict(self) -> Dict[str, Any]:
            return {
                "source_path": self.source_path,
                "document_title": self.document_title,
                "total_pages": self.total_pages,
                "chunks": [c.to_dict() for c in self.chunks],
                "table_of_contents": self.table_of_contents,
                "parsing_metadata": self.parsing_metadata,
            }

    DocumentProcessor = None
    get_document_processor = lambda: None


__all__ = [
    "VectorDBFormatter",
    "RAGCitationBuilder",
    "NON_VEGAN_KEYWORDS",
    "UnifiedIngestionTool",
    "IngestionPayload",
    "filter_vegan_text",
    "ingest_source",
    "parse_pdf_url",
    "scrape_menu",
    "ChunkedDocument",
    "TableAwareChunk",
]
