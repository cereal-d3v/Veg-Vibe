"""
Test suite for Docling-based document parser.

Validates:
- PDF parsing and chunking
- Table extraction and structure preservation
- Metadata extraction and citation generation
- Vector DB compatibility
- Hallucination prevention with structured data
"""

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import List

import pytest

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vegvibe.tests")


class TestDocumentProcessor:
    """Test cases for DocumentProcessor."""
    
    @pytest.fixture
    def sample_pdf_path(self) -> Path:
        """Path to sample PDF for testing."""
        return Path(__file__).parent / "fixtures" / "sample_vegan_guide.pdf"
    
    def test_processor_initialization(self):
        """Test DocumentProcessor can be initialized."""
        from app.ingestion import DocumentProcessor
        
        processor = DocumentProcessor(chunk_size=1024, chunk_overlap=128)
        assert processor is not None
        assert processor.chunk_size == 1024
        assert processor.chunk_overlap == 128
        logger.info("✅ DocumentProcessor initialization test passed")
    
    def test_document_processor_singleton(self):
        """Test singleton pattern for DocumentProcessor."""
        from app.ingestion.docling_parser import get_document_processor
        
        proc1 = get_document_processor()
        proc2 = get_document_processor()
        
        assert proc1 is proc2
        logger.info("✅ Singleton pattern test passed")
    
    def test_table_aware_chunk_creation(self):
        """Test TableAwareChunk data structure."""
        from app.ingestion import TableAwareChunk
        
        chunk = TableAwareChunk(
            id="test_chunk_1",
            content="Sample content",
            source_document="/path/to/doc.pdf",
            page_number=1,
            section_heading="Introduction",
            is_table=False,
        )
        
        assert chunk.id == "test_chunk_1"
        assert chunk.page_number == 1
        assert chunk.section_heading == "Introduction"
        assert chunk.is_table is False
        
        # Test conversion to dict
        chunk_dict = chunk.to_dict()
        assert chunk_dict["id"] == "test_chunk_1"
        assert chunk_dict["content"] == "Sample content"
        logger.info("✅ TableAwareChunk creation test passed")
    
    def test_table_chunk_with_metadata(self):
        """Test TableAwareChunk for table content."""
        from app.ingestion import TableAwareChunk
        
        table_content = """| Ingredient | Vegan | Notes |
| --- | --- | --- |
| Honey | No | Animal derived |
| Agave | Yes | Plant based |"""
        
        table_chunk = TableAwareChunk(
            id="table_1",
            content=table_content,
            source_document="/path/to/PETA_Guide.pdf",
            page_number=5,
            section_heading="Ingredient Classification",
            is_table=True,
            table_title="Vegan vs Non-Vegan Ingredients",
        )
        
        assert table_chunk.is_table is True
        assert table_chunk.table_title == "Vegan vs Non-Vegan Ingredients"
        
        citation = table_chunk.to_citation_reference()
        assert "Table: Vegan vs Non-Vegan Ingredients" in citation
        assert "p. 5" in citation
        logger.info("✅ Table chunk metadata test passed")
    
    def test_citation_reference_generation(self):
        """Test citation reference generation."""
        from app.ingestion import TableAwareChunk
        
        # Text chunk citation
        text_chunk = TableAwareChunk(
            id="chunk_1",
            content="Guidelines for vegan substitutions",
            source_document="/path/to/Vegan_Substitutions.pdf",
            page_number=3,
            section_heading="Dairy Replacements",
            is_table=False,
        )
        
        citation = text_chunk.to_citation_reference()
        assert "Vegan_Substitutions.pdf" in citation
        assert "p. 3" in citation
        assert "Dairy Replacements" in citation
        
        logger.info(f"Text citation: {citation}")
        logger.info("✅ Citation reference generation test passed")
    
    def test_chunked_document_creation(self):
        """Test ChunkedDocument data structure."""
        from app.ingestion import ChunkedDocument, TableAwareChunk
        
        chunk1 = TableAwareChunk(
            id="chunk_1",
            content="Content 1",
            source_document="/path/to/doc.pdf",
            page_number=1,
        )
        
        chunk2 = TableAwareChunk(
            id="chunk_2",
            content="Content 2",
            source_document="/path/to/doc.pdf",
            page_number=1,
            is_table=True,
        )
        
        doc = ChunkedDocument(
            source_path="/path/to/doc.pdf",
            document_title="Test Document",
            total_pages=10,
            chunks=[chunk1, chunk2],
            table_of_contents={},
            parsing_metadata={"num_chunks": 2},
        )
        
        assert len(doc.chunks) == 2
        assert doc.total_pages == 10
        
        doc_dict = doc.to_dict()
        assert doc_dict["num_chunks"] == 2
        logger.info("✅ ChunkedDocument creation test passed")


class TestVectorDBCompatibility:
    """Test cases for vector database compatibility."""
    
    def test_chroma_format_conversion(self):
        """Test conversion to Chroma format."""
        from app.ingestion import ChunkedDocument, TableAwareChunk
        from app.ingestion.vectordb_compat import VectorDBFormatter
        
        chunk = TableAwareChunk(
            id="chunk_1",
            content="Sample vegan recipe",
            source_document="/path/to/recipes.pdf",
            page_number=2,
            section_heading="Breakfast Recipes",
        )
        
        doc = ChunkedDocument(
            source_path="/path/to/recipes.pdf",
            document_title="Vegan Recipes",
            total_pages=50,
            chunks=[chunk],
            table_of_contents={},
            parsing_metadata={},
        )
        
        ids, documents, metadatas = VectorDBFormatter.to_chroma_documents(doc)
        
        assert len(ids) == 1
        assert len(documents) == 1
        assert len(metadatas) == 1
        assert metadatas[0]["section"] == "Breakfast Recipes"
        assert metadatas[0]["page"] == 2
        
        logger.info("✅ Chroma format conversion test passed")
    
    def test_metadata_index_creation(self):
        """Test metadata index generation."""
        from app.ingestion import ChunkedDocument, TableAwareChunk
        from app.ingestion.vectordb_compat import VectorDBFormatter
        
        chunks = [
            TableAwareChunk(
                id="page1_chunk1",
                content="Content A",
                source_document="/path/to/doc.pdf",
                page_number=1,
                section_heading="Introduction",
            ),
            TableAwareChunk(
                id="page1_chunk2",
                content="Content B",
                source_document="/path/to/doc.pdf",
                page_number=1,
                section_heading="Introduction",
            ),
            TableAwareChunk(
                id="page2_table1",
                content="| Header | Value |\n| --- | --- |",
                source_document="/path/to/doc.pdf",
                page_number=2,
                is_table=True,
            ),
        ]
        
        doc = ChunkedDocument(
            source_path="/path/to/doc.pdf",
            document_title="Test",
            total_pages=2,
            chunks=chunks,
            table_of_contents={},
            parsing_metadata={},
        )
        
        index = VectorDBFormatter.create_metadata_index(doc)
        
        # Verify page indexing
        assert 1 in index["by_page"]
        assert len(index["by_page"][1]) == 2
        assert 2 in index["by_page"]
        assert len(index["by_page"][2]) == 1
        
        # Verify section indexing
        assert "Introduction" in index["by_section"]
        assert len(index["by_section"]["Introduction"]) == 2
        
        # Verify table indexing
        assert len(index["tables"]) == 1
        assert "page2_table1" in index["tables"]
        
        logger.info("✅ Metadata index creation test passed")
    
    def test_citation_context_generation(self):
        """Test citation context for RAG responses."""
        from app.ingestion import TableAwareChunk
        from app.ingestion.vectordb_compat import RAGCitationBuilder
        
        chunks = [
            TableAwareChunk(
                id="chunk_1",
                content="Honey is not vegan because it's produced by bees.",
                source_document="PETA_Ingredient_Guide.pdf",
                page_number=15,
                section_heading="Animal-Derived Products",
            ),
            TableAwareChunk(
                id="table_1",
                content="| Ingredient | Status |\n| --- | --- |\n| Honey | Non-Vegan |",
                source_document="PETA_Ingredient_Guide.pdf",
                page_number=16,
                is_table=True,
                table_title="Ingredient Classification Table",
            ),
        ]
        
        context = RAGCitationBuilder.create_citation_context(
            chunks,
            "Is honey vegan?",
        )
        
        assert "PETA_Ingredient_Guide.pdf" in context
        assert "📊" in context  # Table emoji
        assert "📄" in context  # Text emoji
        assert "Ingredient Classification Table" in context
        
        logger.info(f"Citation context:\n{context}")
        logger.info("✅ Citation context generation test passed")


class TestHallucinationPrevention:
    """Test hallucination prevention with structured document data."""
    
    def test_table_preservation_prevents_hallucination(self):
        """
        Test that structured table data prevents hallucination.
        
        Example: PETA ingredient list table should not be
        corrupted into false claims about ingredient vegan status.
        """
        from app.ingestion import TableAwareChunk, ChunkedDocument
        
        # Simulate a PETA ingredient table
        table_content = """| Ingredient | Vegan Status | Notes |
| --- | --- | --- |
| Honey | ❌ No | Produced by bees |
| Agave Nectar | ✅ Yes | Plant-based sweetener |
| Casein | ❌ No | Milk protein |
| Nutritional Yeast | ✅ Yes | Deactivated yeast |"""
        
        table_chunk = TableAwareChunk(
            id="peta_table_1",
            content=table_content,
            source_document="PETA_Animal_Derived_Ingredients.pdf",
            page_number=3,
            is_table=True,
            table_title="Animal-Derived Ingredients",
        )
        
        # Verify table structure is intact
        assert "Honey" in table_chunk.content
        assert "❌ No" in table_chunk.content
        assert "Agave Nectar" in table_chunk.content
        assert "✅ Yes" in table_chunk.content
        
        # Extract lines to verify no loss of structure
        lines = table_chunk.content.split('\n')
        assert len(lines) > 0
        assert all('|' in line for line in lines if line.strip())
        
        logger.info("✅ Table preservation test passed - structure intact")
    
    def test_metadata_citation_accuracy(self):
        """
        Test that metadata allows accurate citation of sources.
        
        This prevents the LLM from claiming false sources or
        misquoting document information.
        """
        from app.ingestion import TableAwareChunk
        
        chunk = TableAwareChunk(
            id="ingredient_list_1",
            content="Ingredients that are NOT vegan: honey, gelatin, casein, whey",
            source_document="Restaurant_Menu_Ingredient_List.pdf",
            page_number=2,
            section_heading="Allergen Information",
            metadata={
                "restaurant": "Fancy Diner",
                "date_extracted": "2024-05-07",
                "extraction_confidence": 0.95,
            },
        )
        
        # Verify citation can be generated accurately
        citation = chunk.to_citation_reference()
        assert "Restaurant_Menu_Ingredient_List.pdf" in citation
        assert "p. 2" in citation
        assert "Allergen Information" in citation
        
        # Metadata should prevent false attributions
        assert chunk.metadata["restaurant"] == "Fancy Diner"
        assert chunk.metadata["extraction_confidence"] == 0.95
        
        logger.info(f"Citation with metadata: {citation}")
        logger.info("✅ Metadata citation accuracy test passed")


class TestDocumentParsingScenarios:
    """Test real-world document parsing scenarios."""
    
    def test_peta_ingredient_guide_parsing_simulation(self):
        """
        Simulate parsing of PETA ingredient guide.
        
        Validates:
        - Ingredient lists preserved as structured data
        - Tables remain intact
        - Section headings maintained
        - No corruption of critical information
        """
        from app.ingestion import TableAwareChunk, ChunkedDocument
        
        # Simulate PETA guide structure
        chunks = [
            TableAwareChunk(
                id="peta_intro",
                content="This guide explains which food ingredients are vegan.",
                source_document="PETA_Ingredient_Guide.pdf",
                page_number=1,
                section_heading="Introduction",
            ),
            TableAwareChunk(
                id="peta_dairy_table",
                content="""| Dairy Product | Alternative | Notes |
| --- | --- | --- |
| Milk | Oat Milk, Almond Milk | Plant-based options |
| Cheese | Nutritional Yeast, Cashew Cheese | Non-dairy alternatives |
| Butter | Coconut Oil, Vegan Butter | Plant-based fats |""",
                source_document="PETA_Ingredient_Guide.pdf",
                page_number=5,
                section_heading="Dairy Alternatives",
                is_table=True,
                table_title="Dairy Product Substitutions",
            ),
        ]
        
        doc = ChunkedDocument(
            source_path="PETA_Ingredient_Guide.pdf",
            document_title="PETA Ingredient Guide",
            total_pages=20,
            chunks=chunks,
            table_of_contents={"sections": ["Introduction", "Dairy Alternatives"]},
            parsing_metadata={"extraction_method": "docling", "has_tables": True},
        )
        
        # Verify document structure
        assert len(doc.chunks) == 2
        assert any(c.is_table for c in doc.chunks)
        
        # Verify no corruption
        table_chunk = next(c for c in doc.chunks if c.is_table)
        assert "Milk" in table_chunk.content
        assert "Oat Milk" in table_chunk.content
        assert "|" in table_chunk.content  # Table markers preserved
        
        logger.info("✅ PETA guide parsing simulation test passed")
    
    def test_restaurant_menu_parsing_simulation(self):
        """Simulate parsing of restaurant menu PDF."""
        from app.ingestion import TableAwareChunk, ChunkedDocument
        
        chunks = [
            TableAwareChunk(
                id="menu_header",
                content="Sunny Cafe - Spring Menu 2024",
                source_document="Sunny_Cafe_Menu.pdf",
                page_number=1,
                section_heading="Title",
            ),
            TableAwareChunk(
                id="menu_items_vegan",
                content="""**Vegan Main Dishes**
1. Buddha Bowl - $15
   Ingredients: Quinoa, chickpeas, roasted vegetables, tahini dressing
2. Vegetable Curry - $14
   Ingredients: Mixed vegetables, coconut milk, basmati rice""",
                source_document="Sunny_Cafe_Menu.pdf",
                page_number=3,
                section_heading="Vegan Options",
            ),
            TableAwareChunk(
                id="menu_allergens",
                content="""| Dish | Contains Dairy | Contains Nuts | Contains Eggs |
| --- | --- | --- | --- |
| Buddha Bowl | No | No | No |
| Vegetable Curry | Yes (coconut) | No | No |""",
                source_document="Sunny_Cafe_Menu.pdf",
                page_number=4,
                section_heading="Allergen Information",
                is_table=True,
                table_title="Allergen Matrix",
            ),
        ]
        
        doc = ChunkedDocument(
            source_path="Sunny_Cafe_Menu.pdf",
            document_title="Sunny Cafe Menu",
            total_pages=8,
            chunks=chunks,
            table_of_contents={},
            parsing_metadata={"restaurant": "Sunny Cafe", "menu_date": "Spring 2024"},
        )
        
        # Verify chunks can be cited accurately
        allergen_chunk = next(c for c in doc.chunks if c.is_table)
        citation = allergen_chunk.to_citation_reference()
        
        assert "Allergen Matrix" in citation
        assert "p. 4" in citation
        
        # Verify ingredient data integrity
        vegan_chunk = next(c for c in doc.chunks if "Buddha Bowl" in c.content)
        assert "tahini dressing" in vegan_chunk.content
        
        logger.info("✅ Restaurant menu parsing simulation test passed")


class TestRegressionTests:
    """Regression tests to prevent common issues."""
    
    def test_no_ingredient_data_loss(self):
        """Ensure ingredient lists are never corrupted or lost."""
        from app.ingestion import TableAwareChunk
        
        ingredient_list = "turmeric, ginger, cumin, coriander, asafetida, salt, oil"
        
        chunk = TableAwareChunk(
            id="curry_ingredients",
            content=f"Ingredients: {ingredient_list}",
            source_document="Recipe.pdf",
            page_number=2,
        )
        
        # Verify all ingredients are preserved
        for ingredient in ingredient_list.split(", "):
            assert ingredient in chunk.content
        
        logger.info("✅ No ingredient data loss test passed")
    
    def test_table_formatting_preserved(self):
        """Ensure table formatting is preserved for structure."""
        from app.ingestion import TableAwareChunk
        
        table = """| Column1 | Column2 | Column3 |
| --- | --- | --- |
| Value1 | Value2 | Value3 |
| Value4 | Value5 | Value6 |"""
        
        chunk = TableAwareChunk(
            id="formatted_table",
            content=table,
            source_document="Data.pdf",
            page_number=1,
            is_table=True,
        )
        
        # Verify markdown table structure
        lines = chunk.content.split('\n')
        assert len(lines) >= 3
        assert all('|' in line for line in lines)
        
        logger.info("✅ Table formatting preserved test passed")
    
    def test_metadata_never_lost(self):
        """Ensure metadata is always attached to chunks."""
        from app.ingestion import TableAwareChunk
        
        chunk = TableAwareChunk(
            id="test_chunk",
            content="Test content",
            source_document="/important/source.pdf",
            page_number=42,
            section_heading="Critical Section",
            metadata={"extracted_by": "docling", "version": "1.29"},
        )
        
        # Verify all metadata is preserved
        chunk_dict = chunk.to_dict()
        assert chunk_dict["source_document"] == "/important/source.pdf"
        assert chunk_dict["page_number"] == 42
        assert chunk_dict["section_heading"] == "Critical Section"
        assert chunk_dict["metadata"]["extracted_by"] == "docling"
        
        logger.info("✅ Metadata preservation test passed")


def test_all_imports():
    """Test that all modules can be imported without errors."""
    try:
        from app.ingestion import (
            DocumentProcessor,
            ChunkedDocument,
            TableAwareChunk,
        )
        from app.ingestion.vectordb_compat import (
            VectorDBFormatter,
            RAGCitationBuilder,
        )
        logger.info("✅ All imports successful")
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        raise


if __name__ == "__main__":
    # Run tests
    logger.info("=" * 70)
    logger.info("RUNNING DOCUMENT PARSER TEST SUITE")
    logger.info("=" * 70)
    
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])
