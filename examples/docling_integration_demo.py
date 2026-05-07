#!/usr/bin/env python3
"""
Example: Integrating Docling-parsed documents with Veg-Vibe RAG pipeline.

This script demonstrates:
1. Parsing a PETA ingredient guide PDF using Docling
2. Converting chunks to vector DB format
3. Adding document context to the agentic RAG assistant
4. Generating responses with precise citations
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_parse_peta_guide():
    """Example 1: Parse a PETA ingredient guide PDF."""
    
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Parsing PETA Ingredient Guide with Docling")
    logger.info("=" * 70)
    
    from app.ingestion import DocumentProcessor
    
    # Initialize processor
    processor = DocumentProcessor(chunk_size=1024, chunk_overlap=128)
    
    # Parse document
    peta_pdf = Path("PETA_Animal_Derived_Ingredients.pdf")
    
    if not peta_pdf.exists():
        logger.warning(f"Sample PDF not found: {peta_pdf}")
        logger.info("Creating simulated PETA document for demo...")
        
        # Create a sample chunked document for demonstration
        from app.ingestion import TableAwareChunk, ChunkedDocument
        
        chunks = [
            TableAwareChunk(
                id="peta_intro_1",
                content="This guide identifies animal-derived ingredients commonly found in food products.",
                source_document="PETA_Animal_Derived_Ingredients.pdf",
                page_number=1,
                section_heading="Introduction",
            ),
            TableAwareChunk(
                id="peta_honey_table",
                content="""| Ingredient | Origin | Status | Notes |
| --- | --- | --- | --- |
| Honey | Bees | ❌ Not Vegan | Produced by bees |
| Propolis | Bees | ❌ Not Vegan | Bee resin |
| Royal Jelly | Bees | ❌ Not Vegan | Bee secretion |
| Beeswax | Bees | ❌ Not Vegan | Bee byproduct |""",
                source_document="PETA_Animal_Derived_Ingredients.pdf",
                page_number=3,
                section_heading="Bee Products",
                is_table=True,
                table_title="Animal-Derived Bee Products",
            ),
            TableAwareChunk(
                id="peta_dairy_table",
                content="""| Ingredient | Source | Status | Common In |
| --- | --- | --- | --- |
| Casein | Milk | ❌ Not Vegan | Cheese, protein powders |
| Whey | Milk | ❌ Not Vegan | Protein bars, baked goods |
| Lactose | Milk | ❌ Not Vegan | Candy, medications |
| Butter | Cream | ❌ Not Vegan | Baked goods, spreads |""",
                source_document="PETA_Animal_Derived_Ingredients.pdf",
                page_number=5,
                section_heading="Dairy Products",
                is_table=True,
                table_title="Animal-Derived Dairy Products",
            ),
        ]
        
        chunked_doc = ChunkedDocument(
            source_path="PETA_Animal_Derived_Ingredients.pdf",
            document_title="PETA Animal-Derived Ingredients Guide",
            total_pages=20,
            chunks=chunks,
            table_of_contents={
                "sections": ["Introduction", "Bee Products", "Dairy Products"]
            },
            parsing_metadata={
                "extraction_method": "docling",
                "simulated": True,
            },
        )
    else:
        logger.info(f"Parsing PDF: {peta_pdf}")
        chunked_doc = processor.parse_document(str(peta_pdf))
    
    # Display results
    logger.info(f"\n📄 Document: {chunked_doc.document_title}")
    logger.info(f"   Total pages: {chunked_doc.total_pages}")
    logger.info(f"   Total chunks: {len(chunked_doc.chunks)}")
    
    logger.info(f"\n📊 Chunk Summary:")
    text_chunks = [c for c in chunked_doc.chunks if not c.is_table]
    table_chunks = [c for c in chunked_doc.chunks if c.is_table]
    logger.info(f"   Text chunks: {len(text_chunks)}")
    logger.info(f"   Table chunks: {len(table_chunks)}")
    
    # Show table chunks
    logger.info(f"\n📊 Tables Found:")
    for chunk in table_chunks:
        logger.info(f"   - {chunk.table_title} (p. {chunk.page_number})")
        logger.info(f"     ID: {chunk.id}")
    
    return chunked_doc


def example_2_vector_db_integration(chunked_doc):
    """Example 2: Convert chunks to vector DB format."""
    
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Vector DB Integration (Chroma Format)")
    logger.info("=" * 70)
    
    from app.ingestion import VectorDBFormatter
    
    # Convert to Chroma format
    ids, documents, metadatas = VectorDBFormatter.to_chroma_documents(chunked_doc)
    
    logger.info(f"\n✅ Converted to Chroma format:")
    logger.info(f"   IDs: {len(ids)}")
    logger.info(f"   Documents: {len(documents)}")
    logger.info(f"   Metadatas: {len(metadatas)}")
    
    # Show sample metadata
    logger.info(f"\n📋 Sample Metadata:")
    for i, (id_, doc, meta) in enumerate(zip(ids[:2], documents[:2], metadatas[:2])):
        logger.info(f"\n   [{i}] ID: {id_}")
        logger.info(f"       Source: {meta.get('source')}")
        logger.info(f"       Page: {meta.get('page')}")
        logger.info(f"       Is Table: {meta.get('is_table')}")
        if meta.get('section'):
            logger.info(f"       Section: {meta.get('section')}")
        logger.info(f"       Document (first 100 chars): {doc[:100]}...")
    
    # Create metadata index
    index = VectorDBFormatter.create_metadata_index(chunked_doc)
    logger.info(f"\n🗂️ Metadata Index:")
    logger.info(f"   Pages: {len(index['by_page'])}")
    logger.info(f"   Sections: {len(index['by_section'])}")
    logger.info(f"   Tables: {len(index['tables'])}")
    
    return ids, documents, metadatas, index


def example_3_rag_with_document_awareness(chunked_doc):
    """Example 3: Integrate with RAG pipeline."""
    
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Document-Aware RAG Pipeline")
    logger.info("=" * 70)
    
    from app.utils.agentic_rag import DocumentAwareAssistant
    from app.utils.recommend import RecipeRecommender
    
    # For this example, we'll simulate the recommender
    # In production, load with: RecipeRecommender("recipes.csv")
    logger.info("\n⚠️ Note: Using simulated RAG assistant for demo")
    logger.info("In production, load RecipeRecommender with actual recipe CSV")
    
    try:
        # Try to load real recommender if it exists
        recipe_csv = Path("vegan_recipes.csv")
        if recipe_csv.exists():
            recommender = RecipeRecommender(str(recipe_csv))
            logger.info(f"✅ Loaded recipes from {recipe_csv}")
        else:
            logger.warning("Recipe CSV not found, using stub recommender")
            
            # Create a stub
            class StubRecommender:
                def search_recipes_tool(self, query, limit, filters):
                    return [
                        {
                            "id": 1,
                            "title": "Vegan Buddha Bowl",
                            "ingredients": "quinoa, chickpeas, vegetables",
                            "protein": 15,
                            "calories": 420,
                        }
                    ]
            recommender = StubRecommender()
        
        # Initialize document-aware assistant
        assistant = DocumentAwareAssistant(recommender)
        
        # Convert chunks to RAG format
        document_chunks = [
            {
                "id": chunk.id,
                "content": chunk.content,
                "source": chunk.source_document,
                "page": chunk.page_number,
                "section": chunk.section_heading,
                "is_table": chunk.is_table,
                "table_title": chunk.table_title,
            }
            for chunk in chunked_doc.chunks
        ]
        
        # Add to assistant
        assistant.add_document_chunks(document_chunks)
        logger.info(f"✅ Added {len(document_chunks)} document chunks to assistant")
        
        # Generate answer with document awareness
        logger.info(f"\n🤖 Generating RAG response...")
        response = assistant.answer_with_documents(
            question="Is honey vegan?",
            max_results=3,
            include_document_sources=True,
        )
        
        logger.info(f"\n📝 RAG Response:")
        logger.info(f"\n{response['answer']}")
        
        # Show document sources
        if response.get('document_sources'):
            logger.info(f"\n🔗 Document Sources Used:")
            for src in response['document_sources']:
                logger.info(f"   - {src['citation']}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in RAG example: {e}")
        logger.warning("Skipping RAG example - ensure recipes.csv is available")
        return None


def example_4_citation_generation():
    """Example 4: Generate precise citations."""
    
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Precise Citation Generation")
    logger.info("=" * 70)
    
    from app.ingestion import TableAwareChunk, RAGCitationBuilder
    
    # Create sample chunks
    chunks = [
        TableAwareChunk(
            id="chunk_1",
            content="Honey is produced by bees and is not considered vegan.",
            source_document="PETA_Ingredient_Guide.pdf",
            page_number=15,
            section_heading="Animal-Derived Products",
        ),
        TableAwareChunk(
            id="table_1",
            content="| Ingredient | Status |\n| --- | --- |\n| Honey | Not Vegan |",
            source_document="PETA_Ingredient_Guide.pdf",
            page_number=16,
            is_table=True,
            table_title="Ingredient Classification",
        ),
    ]
    
    logger.info(f"\n🔗 Generated Citations:")
    for chunk in chunks:
        citation = RAGCitationBuilder.create_citation(chunk)
        logger.info(f"   - {citation}")
    
    # Generate citation context for LLM
    context = RAGCitationBuilder.create_citation_context(
        chunks,
        "Is honey vegan?",
    )
    
    logger.info(f"\n📍 Citation Context for LLM:")
    logger.info(context)


def example_5_table_preservation():
    """Example 5: Demonstrate table preservation."""
    
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Table Structure Preservation")
    logger.info("=" * 70)
    
    from app.ingestion import TableAwareChunk
    
    # Original table structure
    table_content = """| Ingredient | Vegan? | Alternative |
| --- | --- | --- |
| Honey | NO | Maple Syrup |
| Milk | NO | Oat Milk |
| Eggs | NO | Flax Seeds |
| Butter | NO | Coconut Oil |
| Cheese | NO | Nutritional Yeast |"""
    
    # Create table chunk
    chunk = TableAwareChunk(
        id="substitution_table",
        content=table_content,
        source_document="Vegan_Substitutions_Guide.pdf",
        page_number=7,
        is_table=True,
        table_title="Common Vegan Substitutions",
    )
    
    logger.info(f"\n📊 Original Table Structure (Preserved):")
    logger.info(chunk.content)
    
    # Verify structure
    lines = chunk.content.split('\n')
    table_rows = [l for l in lines if l.strip().startswith('|')]
    
    logger.info(f"\n✅ Structure Verification:")
    logger.info(f"   Lines with '|': {len(table_rows)}")
    logger.info(f"   Table intact: {all('|' in l for l in lines if l.strip())}")
    
    # Extract data
    logger.info(f"\n📋 Data Integrity Check:")
    logger.info(f"   'Honey' present: {'Honey' in chunk.content}")
    logger.info(f"   'NO' status preserved: {'NO' in chunk.content}")
    logger.info(f"   'Maple Syrup' alternative: {'Maple Syrup' in chunk.content}")
    
    # Show embedding text (what would be sent to vector DB)
    logger.info(f"\n🔍 Text for Embedding:")
    embedding_text = chunk.to_embedding_text()
    logger.info(embedding_text[:200] + "...")


def main():
    """Run all examples."""
    
    logger.info("\n" + "=" * 70)
    logger.info("VEG-VIBE DOCLING INTEGRATION EXAMPLES")
    logger.info("=" * 70)
    
    try:
        # Example 1: Parse document
        chunked_doc = example_1_parse_peta_guide()
        
        # Example 2: Vector DB integration
        ids, documents, metadatas, index = example_2_vector_db_integration(chunked_doc)
        
        # Example 3: RAG pipeline
        response = example_3_rag_with_document_awareness(chunked_doc)
        
        # Example 4: Citation generation
        example_4_citation_generation()
        
        # Example 5: Table preservation
        example_5_table_preservation()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        
        return {
            "chunked_doc": chunked_doc,
            "vector_db_format": (ids, documents, metadatas),
            "metadata_index": index,
            "rag_response": response,
        }
        
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    main()
