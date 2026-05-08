import logging
import os
from typing import Any, Dict, List, Optional

from app.ingestion import ChunkedDocument
from app.ingestion.vectordb_compat import VectorDBFormatter

logger = logging.getLogger("vegvibe.vector_store")


class ChromaVectorStore:
    """ChromaDB-backed vector store with hybrid search support."""

    def __init__(
        self,
        collection_name: str = "vegvibe_ingestion",
        persist_directory: Optional[str] = None,
    ):
        if persist_directory is None:
            persist_directory = os.getenv("CHROMA_DB_PATH", "./backend/chroma_db")

        import chromadb

        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)

        logger.info(
            "ChromaVectorStore ready (collection=%s, path=%s)",
            collection_name,
            persist_directory,
        )

    @staticmethod
    def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Chroma supports scalar metadata values; normalize nested values to strings."""

        sanitized: Dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized

    def upsert_chunked_document(
        self,
        chunked_doc: ChunkedDocument,
        source_url: Optional[str] = None,
    ) -> int:
        """Store Docling chunks in Chroma with reliability metadata fields."""

        ids, documents, metadatas = VectorDBFormatter.to_chroma_documents(chunked_doc)

        enriched: List[Dict[str, Any]] = []
        for chunk, base_meta in zip(chunked_doc.chunks, metadatas):
            meta = dict(base_meta)
            meta["source_url"] = source_url or chunk.source_document
            meta["page_number"] = chunk.page_number
            meta["document_section"] = chunk.section_heading or ""
            meta["is_table"] = bool(chunk.is_table)
            enriched.append(self._sanitize_metadata(meta))

        self.collection.upsert(ids=ids, documents=documents, metadatas=enriched)
        logger.info("Upserted %s chunks into Chroma", len(ids))
        return len(ids)

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Run vector similarity retrieval in Chroma."""

        result = self.collection.query(
            query_texts=[query],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        rows: List[Dict[str, Any]] = []
        for item_id, doc, meta, distance in zip(ids, documents, metadatas, distances):
            semantic_score = max(0.0, 1.0 - float(distance or 0.0))
            rows.append(
                {
                    "id": item_id,
                    "content": doc or "",
                    "metadata": meta or {},
                    "semantic_score": semantic_score,
                    "distance": float(distance or 0.0),
                }
            )

        return rows

    def keyword_search(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Run exact keyword retrieval for reliability-sensitive terms (e.g. brand names)."""

        result = self.collection.get(
            where_document={"$contains": query},
            include=["documents", "metadatas"],
        )

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        q = query.lower()
        rows: List[Dict[str, Any]] = []
        for item_id, doc, meta in zip(ids, documents, metadatas):
            content = doc or ""
            lowered = content.lower()
            occurrences = lowered.count(q)
            if occurrences <= 0:
                continue

            rows.append(
                {
                    "id": item_id,
                    "content": content,
                    "metadata": meta or {},
                    "keyword_score": float(occurrences),
                    "exact_match": q in lowered,
                }
            )

        rows.sort(key=lambda x: (x["keyword_score"], x["exact_match"]), reverse=True)
        return rows[:limit]

    def hybrid_search(
        self,
        query: str,
        limit: int = 5,
        semantic_limit: int = 20,
        keyword_limit: int = 50,
        semantic_weight: float = 0.65,
        keyword_weight: float = 0.35,
    ) -> List[Dict[str, Any]]:
        """Blend semantic and keyword retrieval and boost exact matches."""

        semantic_hits = self.semantic_search(query=query, limit=semantic_limit)
        keyword_hits = self.keyword_search(query=query, limit=keyword_limit)

        semantic_by_id = {hit["id"]: hit for hit in semantic_hits}
        keyword_by_id = {hit["id"]: hit for hit in keyword_hits}

        max_keyword = max((hit["keyword_score"] for hit in keyword_hits), default=1.0)

        merged: List[Dict[str, Any]] = []
        for item_id in set(semantic_by_id.keys()) | set(keyword_by_id.keys()):
            semantic = semantic_by_id.get(item_id, {})
            keyword = keyword_by_id.get(item_id, {})

            semantic_score = float(semantic.get("semantic_score", 0.0))
            keyword_raw = float(keyword.get("keyword_score", 0.0))
            keyword_score = keyword_raw / max_keyword if max_keyword > 0 else 0.0

            exact_match = bool(keyword.get("exact_match", False))
            exact_bonus = 0.15 if exact_match else 0.0
            score = (
                (semantic_weight * semantic_score)
                + (keyword_weight * keyword_score)
                + exact_bonus
            )

            merged.append(
                {
                    "id": item_id,
                    "content": semantic.get("content") or keyword.get("content") or "",
                    "metadata": semantic.get("metadata") or keyword.get("metadata") or {},
                    "semantic_score": semantic_score,
                    "keyword_score": keyword_score,
                    "exact_match": exact_match,
                    "score": score,
                }
            )

        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:limit]
