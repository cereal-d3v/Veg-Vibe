from app.ingestion import ChunkedDocument, TableAwareChunk
from app.services.vector_store import ChromaVectorStore


class _FakeCollection:
    def __init__(self):
        self.last_upsert = None

    def upsert(self, ids, documents, metadatas):
        self.last_upsert = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }


def test_upsert_chunked_document_stores_required_metadata_fields():
    store = ChromaVectorStore.__new__(ChromaVectorStore)
    store.collection = _FakeCollection()

    chunk = TableAwareChunk(
        id="chunk-1",
        content="BrandX oat milk ingredients",
        source_document="/tmp/doc.pdf",
        page_number=3,
        section_heading="Ingredients",
    )
    doc = ChunkedDocument(
        source_path="/tmp/doc.pdf",
        document_title="Sample Doc",
        total_pages=8,
        chunks=[chunk],
        table_of_contents={},
        parsing_metadata={},
    )

    count = store.upsert_chunked_document(doc, source_url="https://example.com/menu.pdf")

    assert count == 1
    payload = store.collection.last_upsert
    assert payload is not None
    metadata = payload["metadatas"][0]

    assert metadata["source_url"] == "https://example.com/menu.pdf"
    assert metadata["page_number"] == 3
    assert metadata["document_section"] == "Ingredients"


def test_hybrid_search_prioritizes_exact_keyword_match():
    store = ChromaVectorStore.__new__(ChromaVectorStore)

    store.semantic_search = lambda query, limit=10: [
        {
            "id": "semantic-only",
            "content": "A similar vegan milk alternative",
            "metadata": {},
            "semantic_score": 0.92,
            "distance": 0.08,
        },
        {
            "id": "brand-hit",
            "content": "BrandX oat milk ingredient list",
            "metadata": {},
            "semantic_score": 0.80,
            "distance": 0.20,
        },
    ]
    store.keyword_search = lambda query, limit=25: [
        {
            "id": "brand-hit",
            "content": "BrandX oat milk ingredient list",
            "metadata": {},
            "keyword_score": 3.0,
            "exact_match": True,
        }
    ]

    results = store.hybrid_search(query="BrandX", limit=2)

    assert len(results) == 2
    assert results[0]["id"] == "brand-hit"
    assert results[0]["exact_match"] is True
