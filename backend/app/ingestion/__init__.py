"""
Data ingestion module for Veg-Vibe.

Handles high-fidelity document parsing using Docling with
table-aware chunking and metadata preservation.

Modules:
- docling_parser: Core document parsing with Docling
- vectordb_compat: Vector database compatibility layer
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

__all__ = [
    "DocumentProcessor",
    "ChunkedDocument",
    "TableAwareChunk",
    "get_document_processor",
    "VectorDBFormatter",
    "RAGCitationBuilder",
]
