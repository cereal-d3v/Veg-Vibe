"""Tests for the unified ingestion tool."""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vegvibe.tests.unified_ingestion")


class TestVeganFilter:
    def test_filter_detects_non_vegan_keywords(self):
        from app.ingestion import filter_vegan_text

        result = filter_vegan_text(
            "This menu item contains whey, gelatin, and tomato sauce."
        )

        assert result["is_vegan"] is False
        assert "whey" in result["matched_keywords"]
        assert "gelatin" in result["matched_keywords"]

    def test_filter_passes_clean_text(self):
        from app.ingestion import filter_vegan_text

        result = filter_vegan_text("Roasted vegetables with rice and herbs.")

        assert result["is_vegan"] is True
        assert result["matched_keywords"] == []


class TestMenuScraping:
    def test_scrape_menu_returns_markdown(self, monkeypatch):
        from app.ingestion import scrape_menu
        import app.ingestion.unified_ingestion as unified_ingestion

        monkeypatch.setattr(
            unified_ingestion,
            "trafilatura_fetch_url",
            lambda url: "<html><body><h1>Menu</h1></body></html>",
        )
        monkeypatch.setattr(
            unified_ingestion,
            "trafilatura_extract",
            lambda downloaded, **kwargs: "# Menu\n\n## Vegan Bowls\n- Chickpeas\n",
        )

        markdown = scrape_menu("https://example.com/menu")

        assert markdown.startswith("# Menu")
        assert "Vegan Bowls" in markdown


class TestPdfIngestion:
    def test_parse_pdf_url_cleans_up_temp_file(self, monkeypatch, tmp_path):
        from app.ingestion import ChunkedDocument, TableAwareChunk, parse_pdf_url
        import app.ingestion.unified_ingestion as unified_ingestion

        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 sample")

        expected_chunk = TableAwareChunk(
            id="sample_p1_c0",
            content="# Sample\n\n| Ingredient | Status |\n| --- | --- |\n| Beans | Vegan |",
            source_document=str(pdf_path),
            page_number=1,
            is_table=True,
            table_title="Ingredient Table",
        )
        fake_document = ChunkedDocument(
            source_path=str(pdf_path),
            document_title="Sample",
            total_pages=1,
            chunks=[expected_chunk],
            table_of_contents={},
            parsing_metadata={"num_chunks": 1},
        )

        class FakeProcessor:
            def parse_document(self, path: str):
                assert Path(path).name == pdf_path.name
                return fake_document

        monkeypatch.setattr(
            unified_ingestion,
            "_download_pdf",
            lambda pdf_url, timeout=60: pdf_path,
        )

        result = parse_pdf_url(
            "https://example.com/sample.pdf",
            processor=FakeProcessor(),
        )

        assert result.document_title == "Sample"
        assert len(result.chunks) == 1
        assert not pdf_path.exists()

    def test_unified_ingestion_dispatches_by_type(self, monkeypatch):
        from app.ingestion import ChunkedDocument, IngestionPayload, ingest_source
        import app.ingestion.unified_ingestion as unified_ingestion

        monkeypatch.setattr(
            unified_ingestion,
            "parse_pdf_url",
            lambda source_url, timeout=60, processor=None: ChunkedDocument(
                source_path=source_url,
                document_title="PETA Guide",
                total_pages=1,
                chunks=[],
                table_of_contents={},
                parsing_metadata={},
            ),
        )
        monkeypatch.setattr(
            unified_ingestion,
            "scrape_menu",
            lambda source_url, timeout=60: "# Vegan Menu\n\nNo whey here.",
        )

        pdf_payload = ingest_source("https://example.com/guide.pdf", source_type="pdf")
        assert isinstance(pdf_payload, IngestionPayload)
        assert pdf_payload.source_type == "pdf"
        assert pdf_payload.is_vegan is True

        menu_payload = ingest_source("https://example.com/menu", source_type="menu")
        assert isinstance(menu_payload, IngestionPayload)
        assert menu_payload.source_type == "menu"
        assert menu_payload.is_vegan is False
        assert "whey" in menu_payload.matched_keywords
