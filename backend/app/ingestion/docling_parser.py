"""
High-fidelity document parsing using Docling.

Implements DocumentProcessor class that:
- Parses PDFs using DocumentConverter from Docling
- Preserves table structures with TableAwareChunk
- Extracts metadata (page numbers, headings, section info)
- Provides RAG-ready output compatible with vector DBs
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docling.document_converter import DocumentConverter
from docling.parsers.pdf_parser import PdfParser

logger = logging.getLogger("vegvibe.ingestion")


@dataclass
class TableAwareChunk:
    """A chunk of document content with metadata."""
    
    id: str  # Unique chunk ID (e.g., "doc_page_3_chunk_2")
    content: str  # The actual text content (Markdown format)
    source_document: str  # Path to source document
    page_number: int  # 1-indexed page number
    section_heading: Optional[str] = None  # Parent heading if applicable
    is_table: bool = False  # True if this chunk contains a table
    table_title: Optional[str] = None  # Title/caption of table if applicable
    confidence: float = 1.0  # Docling confidence score (0-1)
    metadata: Dict[str, Any] = None  # Additional metadata dict
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for vector DB storage."""
        data = asdict(self)
        return data
    
    def to_embedding_text(self) -> str:
        """Return text suitable for embedding."""
        parts = [self.content]
        if self.section_heading:
            parts.insert(0, f"Section: {self.section_heading}")
        if self.is_table and self.table_title:
            parts.insert(0, f"Table: {self.table_title}")
        return "\n".join(parts)
    
    def to_citation_reference(self) -> str:
        """Return citation-friendly reference string."""
        citation = f"{Path(self.source_document).name} (p. {self.page_number})"
        if self.is_table and self.table_title:
            citation += f", Table: {self.table_title}"
        elif self.section_heading:
            citation += f", Section: {self.section_heading}"
        return citation


@dataclass
class ChunkedDocument:
    """Result of parsing and chunking a document."""
    
    source_path: str  # Path to source PDF
    document_title: str  # Extracted title or filename
    total_pages: int
    chunks: List[TableAwareChunk]
    table_of_contents: Dict[str, Any]  # Extracted TOC structure if available
    parsing_metadata: Dict[str, Any]  # Docling extraction stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_path": self.source_path,
            "document_title": self.document_title,
            "total_pages": self.total_pages,
            "num_chunks": len(self.chunks),
            "chunks": [c.to_dict() for c in self.chunks],
            "table_of_contents": self.table_of_contents,
            "parsing_metadata": self.parsing_metadata,
        }
    
    def to_json(self, filepath: Path) -> None:
        """Save to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class DocumentProcessor:
    """
    High-fidelity document parser using Docling.
    
    Features:
    - Parses PDFs using DocumentConverter
    - Preserves table structures in Markdown
    - Extracts and maintains metadata (page numbers, headings)
    - Generates chunks suitable for vector DB ingestion
    - Maintains citation-friendly metadata for RAG agent
    """
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 128):
        """
        Initialize DocumentProcessor.
        
        Args:
            chunk_size: Target size for text chunks (chars)
            chunk_overlap: Overlap between chunks for context (chars)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.converter = DocumentConverter()
        logger.info(f"✓ DocumentProcessor initialized (chunk_size={chunk_size}, overlap={chunk_overlap})")
    
    def parse_document(self, pdf_path: str) -> ChunkedDocument:
        """
        Parse a PDF document into chunks using Docling.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ChunkedDocument with parsed content and metadata
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Document not found: {pdf_path}")
        
        logger.info(f"📄 Parsing document: {pdf_path.name}")
        
        # Convert PDF to Docling format
        try:
            doc = self.converter.convert(pdf_path)
            logger.info(f"✓ Docling conversion complete for {pdf_path.name}")
        except Exception as e:
            logger.error(f"❌ Failed to parse {pdf_path.name}: {e}")
            raise
        
        # Extract metadata
        document_title = pdf_path.stem or pdf_path.name
        total_pages = len([p for p in doc.pages]) if hasattr(doc, 'pages') else 1
        
        # Parse Docling output into chunks
        chunks = self._extract_chunks(doc, str(pdf_path))
        
        # Build table of contents from document structure
        toc = self._extract_toc(doc)
        
        parsing_metadata = {
            "converter_version": "docling",
            "num_chunks": len(chunks),
            "total_pages": total_pages,
            "extraction_format": "markdown",
        }
        
        result = ChunkedDocument(
            source_path=str(pdf_path),
            document_title=document_title,
            total_pages=total_pages,
            chunks=chunks,
            table_of_contents=toc,
            parsing_metadata=parsing_metadata,
        )
        
        logger.info(
            f"✅ Successfully parsed {pdf_path.name}: "
            f"{len(chunks)} chunks, {total_pages} pages"
        )
        return result
    
    def _extract_chunks(self, doc: Any, source_path: str) -> List[TableAwareChunk]:
        """
        Extract chunks from Docling document.
        
        Preserves table structures and metadata.
        """
        chunks = []
        chunk_id_counter = 0
        
        # Get Markdown representation (preserves tables and structure)
        markdown_text = doc.export_to_markdown()
        
        # Track current page and section
        current_page = 1
        current_section = None
        
        # Split by pages and sections while preserving tables
        lines = markdown_text.split('\n')
        current_chunk_lines = []
        current_char_count = 0
        is_table_chunk = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Track section headings
            if line.startswith('# '):
                current_section = line[2:].strip()
                logger.debug(f"Found section: {current_section}")
            
            # Detect page breaks
            if '---' in line and i > 0 and i < len(lines) - 1:
                # Flush current chunk before page break
                if current_chunk_lines:
                    chunk = self._create_chunk(
                        chunk_id_counter, current_chunk_lines,
                        source_path, current_page, current_section,
                        is_table_chunk
                    )
                    chunks.append(chunk)
                    chunk_id_counter += 1
                    current_chunk_lines = []
                    current_char_count = 0
                
                current_page += 1
                i += 1
                continue
            
            # Detect table blocks (preserve them completely)
            if line.strip().startswith('|'):
                # Collect entire table
                table_lines = [line]
                i += 1
                # Collect table header separator
                if i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i])
                    i += 1
                # Collect table rows
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i])
                    i += 1
                
                # Create table chunk if content buffer exists
                if current_chunk_lines:
                    chunk = self._create_chunk(
                        chunk_id_counter, current_chunk_lines,
                        source_path, current_page, current_section,
                        False
                    )
                    chunks.append(chunk)
                    chunk_id_counter += 1
                    current_chunk_lines = []
                    current_char_count = 0
                
                # Create table chunk
                table_chunk = self._create_chunk(
                    chunk_id_counter, table_lines,
                    source_path, current_page, current_section,
                    is_table=True, table_title=self._extract_table_title(table_lines)
                )
                chunks.append(table_chunk)
                chunk_id_counter += 1
                continue
            
            # Add line to current chunk
            line_with_newline = line + '\n'
            line_length = len(line_with_newline)
            
            # Check if adding this line exceeds chunk size
            if current_char_count + line_length > self.chunk_size and current_chunk_lines:
                # Flush current chunk
                chunk = self._create_chunk(
                    chunk_id_counter, current_chunk_lines,
                    source_path, current_page, current_section,
                    is_table_chunk
                )
                chunks.append(chunk)
                chunk_id_counter += 1
                
                # Start new chunk with overlap
                current_chunk_lines = self._get_overlap(current_chunk_lines)
                current_char_count = sum(len(l) + 1 for l in current_chunk_lines)
            
            current_chunk_lines.append(line)
            current_char_count += line_length
            i += 1
        
        # Flush remaining content
        if current_chunk_lines:
            chunk = self._create_chunk(
                chunk_id_counter, current_chunk_lines,
                source_path, current_page, current_section,
                is_table_chunk
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(
        self,
        chunk_id: int,
        lines: List[str],
        source_path: str,
        page_number: int,
        section_heading: Optional[str],
        is_table: bool = False,
        table_title: Optional[str] = None,
    ) -> TableAwareChunk:
        """Create a TableAwareChunk from content."""
        chunk_id_str = f"{Path(source_path).stem}_p{page_number}_c{chunk_id}"
        content = '\n'.join(lines).strip()
        
        return TableAwareChunk(
            id=chunk_id_str,
            content=content,
            source_document=source_path,
            page_number=page_number,
            section_heading=section_heading,
            is_table=is_table,
            table_title=table_title,
            confidence=1.0,
            metadata={
                "chunk_index": chunk_id,
                "chunk_type": "table" if is_table else "text",
            },
        )
    
    def _get_overlap(self, lines: List[str]) -> List[str]:
        """Get the last N lines for overlap context."""
        target_chars = self.chunk_overlap
        current_chars = 0
        overlap_lines = []
        
        for line in reversed(lines):
            current_chars += len(line) + 1
            overlap_lines.insert(0, line)
            if current_chars >= target_chars:
                break
        
        return overlap_lines
    
    def _extract_toc(self, doc: Any) -> Dict[str, Any]:
        """Extract table of contents from document."""
        try:
            # Try to extract structure from Docling document
            # This is a simplified implementation
            return {"auto_generated": True, "sections": []}
        except Exception as e:
            logger.warning(f"Could not extract TOC: {e}")
            return {}
    
    def _extract_table_title(self, table_lines: List[str]) -> Optional[str]:
        """Extract table title from context."""
        # Look for text before the table that might be a title
        # This is a simple heuristic
        if table_lines:
            # Check if first line looks like a title
            first_line = table_lines[0].strip()
            if not first_line.startswith('|'):
                return first_line[:100]  # Use first 100 chars as title
        return None


# Singleton instance
_processor_instance: Optional[DocumentProcessor] = None


def get_document_processor(
    chunk_size: int = 1024, chunk_overlap: int = 128
) -> DocumentProcessor:
    """Get or create a DocumentProcessor singleton."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = DocumentProcessor(chunk_size, chunk_overlap)
    return _processor_instance
