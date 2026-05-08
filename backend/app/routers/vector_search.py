from typing import Optional

from fastapi import APIRouter, HTTPException

from app.ingestion import parse_pdf_url
from app.models.vector import (
    HybridSearchRequest,
    HybridSearchResponse,
    PdfIngestionRequest,
    PdfIngestionResponse,
    SearchResultItem,
)
from app.services.vector_store import ChromaVectorStore

router = APIRouter(prefix="/api/vector", tags=["vector-search"])

vector_store: Optional[ChromaVectorStore] = None


def set_vector_store(store: ChromaVectorStore):
    global vector_store
    vector_store = store


@router.post("/ingest/pdf", response_model=PdfIngestionResponse)
async def ingest_pdf(request: PdfIngestionRequest):
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store is not initialized")

    chunked_doc = parse_pdf_url(request.source_url, timeout=request.timeout)
    ingested = vector_store.upsert_chunked_document(
        chunked_doc=chunked_doc,
        source_url=request.source_url,
    )

    return PdfIngestionResponse(
        source_url=request.source_url,
        document_title=chunked_doc.document_title,
        total_pages=chunked_doc.total_pages,
        ingested_chunks=ingested,
    )


@router.post("/search/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store is not initialized")

    if request.semantic_weight + request.keyword_weight <= 0:
        raise HTTPException(
            status_code=400,
            detail="semantic_weight + keyword_weight must be greater than zero",
        )

    hits = vector_store.hybrid_search(
        query=request.query,
        limit=request.limit,
        semantic_limit=request.semantic_limit,
        keyword_limit=request.keyword_limit,
        semantic_weight=request.semantic_weight,
        keyword_weight=request.keyword_weight,
    )

    return HybridSearchResponse(
        query=request.query,
        total_results=len(hits),
        results=[SearchResultItem(**hit) for hit in hits],
    )
