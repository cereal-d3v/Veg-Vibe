from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PdfIngestionRequest(BaseModel):
    source_url: str
    timeout: int = Field(default=60, ge=5, le=300)


class PdfIngestionResponse(BaseModel):
    source_url: str
    document_title: str
    total_pages: int
    ingested_chunks: int


class HybridSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=50)
    semantic_limit: int = Field(default=20, ge=1, le=200)
    keyword_limit: int = Field(default=50, ge=1, le=500)
    semantic_weight: float = Field(default=0.65, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.35, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    semantic_score: float
    keyword_score: float
    exact_match: bool = False


class HybridSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
