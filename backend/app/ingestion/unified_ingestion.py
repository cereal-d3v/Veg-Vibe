"""Unified ingestion helpers for PDF URLs and live menu scraping.

This module combines the Docling-based PDF ingestion flow with a
Trafilatura-based web scraper for restaurant menus, then applies a
simple keyword gate before content is sent to storage or retrieval.
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

import requests

from typing import Any as _Any

try:
    from trafilatura import extract as trafilatura_extract
    from trafilatura import fetch_url as trafilatura_fetch_url
except ImportError:  # pragma: no cover - handled in runtime environments without trafilatura
    trafilatura_extract = None
    trafilatura_fetch_url = None

logger = logging.getLogger("vegvibe.unified_ingestion")

NON_VEGAN_KEYWORDS: tuple[str, ...] = ("casein", "whey", "gelatin")


@dataclass
class IngestionPayload:
    """Structured result for unified ingestion."""

    source_url: str
    source_type: str
    markdown: str
    is_vegan: bool
    matched_keywords: List[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _download_pdf(pdf_url: str, timeout: int = 60) -> Path:
    """Download a PDF URL to a temporary local file."""

    response = requests.get(pdf_url, stream=True, timeout=timeout)
    response.raise_for_status()

    suffix = ".pdf"
    parsed = urlparse(pdf_url)
    if parsed.path.lower().endswith(".pdf"):
        suffix = ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_path = Path(temp_file.name)

    logger.info("Downloaded PDF from %s to %s", pdf_url, temp_path)
    return temp_path


def parse_pdf_url(
    pdf_url: str,
    *,
    timeout: int = 60,
    processor: Optional[_Any] = None,
) -> _Any:
    """Download a PDF URL and parse it with Docling."""

    # Lazy import to avoid importing heavy Docling packages during unit tests
    if processor is None:
        from app.ingestion.docling_parser import get_document_processor

        processor = get_document_processor()
    pdf_path = _download_pdf(pdf_url, timeout=timeout)

    try:
        return processor.parse_document(str(pdf_path))
    finally:
        if pdf_path.exists():
            pdf_path.unlink(missing_ok=True)


def scrape_menu(url: str, *, timeout: int = 30) -> str:
    """Scrape a restaurant menu URL into clean Markdown."""

    if trafilatura_fetch_url is None or trafilatura_extract is None:
        raise ImportError(
            "trafilatura is required for menu scraping; install backend requirements"
        )

    downloaded = trafilatura_fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not fetch content from {url}")

    markdown = trafilatura_extract(
        downloaded,
        output_format="markdown",
        with_metadata=False,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )

    if not markdown:
        raise ValueError(f"Could not extract menu content from {url}")

    logger.info("Scraped menu from %s", url)
    return markdown.strip()


def filter_vegan_text(
    text: str,
    keywords: Sequence[str] = NON_VEGAN_KEYWORDS,
) -> Dict[str, Any]:
    """Check whether extracted text contains disallowed animal-derived keywords."""

    lowered = text.lower()
    matched_keywords = [keyword for keyword in keywords if keyword.lower() in lowered]

    return {
        "is_vegan": len(matched_keywords) == 0,
        "matched_keywords": matched_keywords,
        "checked_keywords": list(keywords),
    }


def ingest_source(
    source_url: str,
    *,
    source_type: str = "auto",
    timeout: int = 60,
    processor: Optional[Any] = None,
) -> IngestionPayload:
    """Ingest a PDF or restaurant menu URL and apply the vegan filter."""

    if source_type == "auto":
        parsed = urlparse(source_url)
        source_type = "pdf" if parsed.path.lower().endswith(".pdf") else "menu"

    if source_type == "pdf":
        chunked_document = parse_pdf_url(
            source_url,
            timeout=timeout,
            processor=processor,
        )
        markdown = "\n\n".join(chunk.content for chunk in chunked_document.chunks)
        metadata: Dict[str, Any] = {
            "document_title": chunked_document.document_title,
            "total_pages": chunked_document.total_pages,
            "num_chunks": len(chunked_document.chunks),
            "table_of_contents": chunked_document.table_of_contents,
            "parsing_metadata": chunked_document.parsing_metadata,
            "chunks": [chunk.to_dict() for chunk in chunked_document.chunks],
        }
    elif source_type == "menu":
        markdown = scrape_menu(source_url, timeout=timeout)
        metadata = {
            "source_type": "menu",
        }
    else:
        raise ValueError(f"Unsupported source_type: {source_type}")

    filter_result = filter_vegan_text(markdown)
    metadata["vegan_filter"] = filter_result

    payload = IngestionPayload(
        source_url=source_url,
        source_type=source_type,
        markdown=markdown,
        is_vegan=filter_result["is_vegan"],
        matched_keywords=filter_result["matched_keywords"],
        metadata=metadata,
    )

    logger.info(
        "Ingested %s as %s (vegan=%s)",
        source_url,
        source_type,
        payload.is_vegan,
    )
    return payload


class UnifiedIngestionTool:
    """Small wrapper for the unified ingestion flow."""

    def __init__(self, timeout: int = 60, processor: Optional[Any] = None):
        self.timeout = timeout
        self.processor = processor

    def ingest(self, source_url: str, source_type: str = "auto") -> IngestionPayload:
        return ingest_source(
            source_url,
            source_type=source_type,
            timeout=self.timeout,
            processor=self.processor,
        )

    def ingest_pdf(self, pdf_url: str) -> ChunkedDocument:
        return parse_pdf_url(pdf_url, timeout=self.timeout, processor=self.processor)

    def scrape_menu(self, url: str) -> str:
        return scrape_menu(url, timeout=self.timeout)

    def filter(self, text: str, keywords: Sequence[str] = NON_VEGAN_KEYWORDS) -> Dict[str, Any]:
        return filter_vegan_text(text, keywords=keywords)


def main() -> None:
    """Command-line entry point for the ingestion tool."""

    parser = argparse.ArgumentParser(description="Veg-Vibe unified ingestion tool")
    parser.add_argument("source_url", help="PDF or menu URL to ingest")
    parser.add_argument(
        "--type",
        dest="source_type",
        default="auto",
        choices=["auto", "pdf", "menu"],
        help="Source type to ingest",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full structured payload as JSON",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for the upstream fetch",
    )

    args = parser.parse_args()
    payload = ingest_source(
        args.source_url,
        source_type=args.source_type,
        timeout=args.timeout,
    )

    if args.json:
        print(payload.to_json())
    else:
        print(payload.markdown)


if __name__ == "__main__":
    main()
