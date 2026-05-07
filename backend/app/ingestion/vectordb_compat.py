"""
Vector database compatibility layer for ingested documents.

Converts TableAwareChunk objects into format suitable for:
- Chroma vector database
- Pinecone
- Weaviate
- Other vector DBs

Maintains full metadata for citation and reliability verification.
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from app.ingestion.docling_parser import ChunkedDocument, TableAwareChunk

logger = logging.getLogger("vegvibe.vectordb_compat")


class VectorDBFormatter:
    """Format chunks for vector database ingestion."""
    
    @staticmethod
    def to_chroma_documents(
        chunked_doc: ChunkedDocument,
    ) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        """
        Convert ChunkedDocument to Chroma format.
        
        Returns:
            (ids, documents, metadatas)
        """
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunked_doc.chunks:
            ids.append(chunk.id)
            documents.append(chunk.to_embedding_text())
            
            metadata = {
                "source": chunk.source_document,
                "page": chunk.page_number,
                "is_table": chunk.is_table,
                "confidence": chunk.confidence,
            }
            
            if chunk.section_heading:
                metadata["section"] = chunk.section_heading
            
            if chunk.table_title:
                metadata["table_title"] = chunk.table_title
            
            # Add custom metadata
            metadata.update(chunk.metadata)
            
            metadatas.append(metadata)
        
        logger.info(f"✅ Formatted {len(ids)} chunks for Chroma")
        return ids, documents, metadatas
    
    @staticmethod
    def to_pinecone_vectors(
        chunked_doc: ChunkedDocument,
        embeddings: List[List[float]],  # Pre-computed embeddings
    ) -> List[Tuple[str, List[float], Dict[str, Any]]]:
        """
        Convert ChunkedDocument to Pinecone format.
        
        Args:
            chunked_doc: Parsed and chunked document
            embeddings: Pre-computed embedding vectors (must match chunk count)
            
        Returns:
            List of (id, vector, metadata) tuples
        """
        if len(embeddings) != len(chunked_doc.chunks):
            raise ValueError(
                f"Embedding count ({len(embeddings)}) does not match "
                f"chunk count ({len(chunked_doc.chunks)})"
            )
        
        vectors = []
        for chunk, embedding in zip(chunked_doc.chunks, embeddings):
            metadata = {
                "source": chunk.source_document,
                "page": chunk.page_number,
                "content": chunk.content[:500],  # Store content preview
                "is_table": chunk.is_table,
                "citation": chunk.to_citation_reference(),
            }
            
            if chunk.section_heading:
                metadata["section"] = chunk.section_heading
            
            if chunk.table_title:
                metadata["table_title"] = chunk.table_title
            
            vectors.append((chunk.id, embedding, metadata))
        
        logger.info(f"✅ Formatted {len(vectors)} vectors for Pinecone")
        return vectors
    
    @staticmethod
    def to_weaviate_objects(
        chunked_doc: ChunkedDocument,
    ) -> List[Dict[str, Any]]:
        """
        Convert ChunkedDocument to Weaviate format.
        
        Returns:
            List of Weaviate object dictionaries
        """
        objects = []
        
        for chunk in chunked_doc.chunks:
            obj = {
                "id": chunk.id,
                "class": "DocumentChunk",
                "properties": {
                    "content": chunk.content,
                    "embedContent": chunk.to_embedding_text(),
                    "source": chunk.source_document,
                    "page": chunk.page_number,
                    "section": chunk.section_heading or "",
                    "isTable": chunk.is_table,
                    "tableTitle": chunk.table_title or "",
                    "confidence": chunk.confidence,
                    "citation": chunk.to_citation_reference(),
                },
            }
            objects.append(obj)
        
        logger.info(f"✅ Formatted {len(objects)} objects for Weaviate")
        return objects
    
    @staticmethod
    def create_metadata_index(
        chunked_doc: ChunkedDocument,
    ) -> Dict[str, List[str]]:
        """
        Create an index of chunks by metadata for efficient retrieval.
        
        Returns:
            Dictionary with keys:
            - by_page: Dict[int, List[str]] (page -> chunk IDs)
            - by_section: Dict[str, List[str]] (section -> chunk IDs)
            - tables: List[str] (chunk IDs of table chunks)
        """
        index = {
            "by_page": {},
            "by_section": {},
            "tables": [],
        }
        
        for chunk in chunked_doc.chunks:
            # Index by page
            if chunk.page_number not in index["by_page"]:
                index["by_page"][chunk.page_number] = []
            index["by_page"][chunk.page_number].append(chunk.id)
            
            # Index by section
            if chunk.section_heading:
                if chunk.section_heading not in index["by_section"]:
                    index["by_section"][chunk.section_heading] = []
                index["by_section"][chunk.section_heading].append(chunk.id)
            
            # Index tables
            if chunk.is_table:
                index["tables"].append(chunk.id)
        
        logger.info(
            f"✅ Created metadata index: "
            f"{len(index['by_page'])} pages, "
            f"{len(index['by_section'])} sections, "
            f"{len(index['tables'])} tables"
        )
        return index


class RAGCitationBuilder:
    """Build citations for RAG responses."""
    
    @staticmethod
    def create_citation(chunk: TableAwareChunk) -> str:
        """Create formatted citation for a chunk."""
        return chunk.to_citation_reference()
    
    @staticmethod
    def create_citations_batch(chunks: List[TableAwareChunk]) -> List[str]:
        """Create citations for multiple chunks."""
        return [chunk.to_citation_reference() for chunk in chunks]
    
    @staticmethod
    def create_citation_context(
        chunks: List[TableAwareChunk],
        query: str,
    ) -> str:
        """
        Create a formatted citation context for injection into RAG response.
        
        Returns:
            Formatted string suitable for inclusion in LLM context.
        """
        lines = [f"🔗 Sources for query: '{query}'\n"]
        
        for i, chunk in enumerate(chunks, 1):
            citation = chunk.to_citation_reference()
            content_preview = chunk.content[:100].replace('\n', ' ')
            
            if chunk.is_table:
                lines.append(
                    f"  {i}. 📊 {citation}\n"
                    f"     (Table - {content_preview}...)"
                )
            else:
                lines.append(
                    f"  {i}. 📄 {citation}\n"
                    f"     (Text - {content_preview}...)"
                )
        
        return "\n".join(lines)
