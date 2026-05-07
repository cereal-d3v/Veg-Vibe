# Document-Aware RAG: Best Practices & Implementation Guide

## Overview

This guide provides best practices for implementing document-aware Retrieval-Augmented Generation (RAG) using Docling and Veg-Vibe's ingestion pipeline.

## Key Principles

### 1. **Preserve Structure, Not Just Text**

❌ **Bad**: Flatten everything to plain text
```
"honey is an ingredient produced by bees and is not considered vegan"
```

✅ **Good**: Keep structure in Markdown
```markdown
| Ingredient | Status |
| --- | --- |
| Honey | Not Vegan |
```

**Why**: LLMs can misunderstand flattened text and invent missing information.

### 2. **Maintain Full Metadata**

Always track:
- **Source Document**: "PETA_Ingredient_Guide.pdf"
- **Page Number**: p. 15
- **Section**: "Animal-Derived Products"
- **Chunk Type**: text vs. table
- **Extraction Confidence**: 0.98

This enables precise citations and verification.

### 3. **Enforce Citation Requirements**

Every claim must be traceable:

```python
# BAD: Vague sourcing
"Honey is not vegan because it comes from bees."

# GOOD: Precise citation
"According to Table 3 in PETA_Ingredient_Guide.pdf (p. 15),
honey is not vegan because it's produced by bees."
```

### 4. **Leverage Table Structure for Reliability**

Tables are your friend for preventing hallucination:

```python
# Tables maintain relationships:
| Product | Source | Vegan |
| --- | --- | --- |
| Honey | Bees | NO |
| Casein | Milk | NO |

# LLM cannot invent: "Almonds (from bees) - NO"
# Because the table clearly shows only honey comes from bees
```

## Implementation Workflow

### Step 1: Parse Documents with Docling

```python
from app.ingestion import DocumentProcessor

processor = DocumentProcessor(chunk_size=1024, chunk_overlap=128)
chunked = processor.parse_document("PETA_Guide.pdf")

print(f"✅ Parsed {len(chunked.chunks)} chunks")
```

### Step 2: Verify Table Integrity

```python
# Ensure tables are preserved
table_chunks = [c for c in chunked.chunks if c.is_table]
for chunk in table_chunks:
    # Verify markdown structure
    assert "|" in chunk.content
    assert "---" in chunk.content or "|" in chunk.content
    print(f"✅ Table preserved: {chunk.table_title}")
```

### Step 3: Convert to Vector DB Format

```python
from app.ingestion import VectorDBFormatter

ids, documents, metadatas = VectorDBFormatter.to_chroma_documents(chunked)

# Store in vector database
collection.add(ids=ids, documents=documents, metadatas=metadatas)
```

### Step 4: Integrate with RAG Pipeline

```python
from app.utils.agentic_rag import DocumentAwareAssistant

assistant = DocumentAwareAssistant(recommender)

# Convert chunks to RAG format
doc_chunks = [
    {
        "id": c.id,
        "content": c.content,
        "source": c.source_document,
        "page": c.page_number,
        "section": c.section_heading,
        "is_table": c.is_table,
        "table_title": c.table_title,
    }
    for c in chunked.chunks
]
assistant.add_document_chunks(doc_chunks)

# Generate answer with citations
response = assistant.answer_with_documents("Is honey vegan?")
print(response["answer"])
```

### Step 5: Verify Grounding

```python
# Check that response doesn't hallucinate
verification = verify_response_grounding(
    response["answer"],
    chunked.chunks,
)

if verification["grounded"]:
    print("✅ Response is grounded in document data")
else:
    print(f"❌ Hallucinations detected: {verification['issues']}")
```

## Code Examples

### Example 1: Parse and Store in Chroma

```python
import chromadb
from app.ingestion import DocumentProcessor, VectorDBFormatter

# Parse document
processor = DocumentProcessor()
chunked = processor.parse_document("PETA_Guide.pdf")

# Convert to Chroma format
ids, documents, metadatas = VectorDBFormatter.to_chroma_documents(chunked)

# Create and populate collection
client = chromadb.Client()
collection = client.create_collection("peta_guides")
collection.add(ids=ids, documents=documents, metadatas=metadatas)

# Query
results = collection.query(
    query_texts=["Is honey vegan?"],
    n_results=5,
)

# Process results
for i, doc_id in enumerate(results["ids"][0]):
    print(f"{i}. ID: {doc_id}")
    print(f"   Document: {results['documents'][0][i][:100]}...")
    print(f"   Metadata: {results['metadatas'][0][i]}")
```

### Example 2: Document-Specific RAG

```python
from app.utils.agentic_rag import DocumentAwareAssistant
from app.ingestion import RAGCitationBuilder

assistant = DocumentAwareAssistant(recommender)

# Add multiple documents
for pdf_path in ["PETA_Guide.pdf", "Restaurant_Menu.pdf"]:
    chunked = processor.parse_document(pdf_path)
    chunks = [
        {
            "id": c.id,
            "content": c.content,
            "source": c.source_document,
            "page": c.page_number,
            "section": c.section_heading,
            "is_table": c.is_table,
            "table_title": c.table_title,
        }
        for c in chunked.chunks
    ]
    assistant.add_document_chunks(chunks)

# Generate response with citations
response = assistant.answer_with_documents(
    "What are vegan alternatives to honey?",
    include_document_sources=True,
)

print(response["answer"])
# Output includes: "According to PETA_Guide.pdf (p. 15)..."
```

### Example 3: Citation Context for LLM

```python
from app.ingestion import RAGCitationBuilder

# Create citation context
supporting_chunks = [chunk1, chunk2, chunk3]
context = RAGCitationBuilder.create_citation_context(
    supporting_chunks,
    "Is honey vegan?",
)

# Inject into LLM prompt
llm_prompt = f"""
Answer this question using ONLY the provided sources:
"{question}"

SOURCES:
{context}

Now answer:
"""

# LLM sees this:
"""
SOURCES:
🔗 Sources for query: 'Is honey vegan?'
  1. 📊 PETA_Guide.pdf (p. 15), Table: Animal Products
     (Table - | Honey | Not Vegan | ...)
  2. 📄 PETA_Guide.pdf (p. 15), Section: Animal-Derived
     (Text - Honey is produced by bees...)

Now answer:
"""
```

### Example 4: Metadata-Driven Queries

```python
from app.ingestion import VectorDBFormatter

# Create metadata index
index = VectorDBFormatter.create_metadata_index(chunked)

# Query by page
chunks_on_page_5 = index["by_page"][5]
print(f"Chunks on page 5: {chunks_on_page_5}")

# Query by section
dairy_chunks = index["by_section"]["Dairy Products"]
print(f"Chunks in dairy section: {dairy_chunks}")

# Query tables only
table_chunks = index["tables"]
print(f"All table chunks: {table_chunks}")
```

### Example 5: Hallucination Prevention Check

```python
def verify_response_grounding(response_text, source_chunks):
    """Check response only references source data."""
    
    # Extract ingredients mentioned in response
    response_ingredients = set()
    for line in response_text.split('\n'):
        if 'ingredient' in line.lower():
            # Parse ingredients from line
            response_ingredients.add(line.lower())
    
    # Extract ingredients in source data
    source_ingredients = set()
    for chunk in source_chunks:
        source_ingredients.update(chunk.content.lower().split())
    
    # Find hallucinated ingredients
    hallucinated = response_ingredients - source_ingredients
    
    if hallucinated:
        print(f"❌ Hallucinated: {hallucinated}")
        return False
    else:
        print(f"✅ Response grounded in source data")
        return True
```

## Common Pitfalls & Solutions

### Pitfall 1: Losing Table Structure

**Problem**: Tables become gibberish during chunking.

**Solution**: Use `is_table=True` flag and preserve Markdown:
```python
# Always check
assert chunk.is_table == True
assert "|" in chunk.content  # Markdown tables
```

### Pitfall 2: Missing Page Information

**Problem**: Can't cite which page information came from.

**Solution**: Always track metadata:
```python
chunk = TableAwareChunk(
    ...,
    page_number=15,  # REQUIRED
    source_document="doc.pdf",  # REQUIRED
    section_heading="Section Name",  # REQUIRED
)
```

### Pitfall 3: Vague Citations

**Problem**: Response says "According to the guide..." (non-specific).

**Solution**: Build specific citations:
```python
citation = RAGCitationBuilder.create_citation(chunk)
# Output: "PETA_Guide.pdf (p. 15), Table: Ingredients"
```

### Pitfall 4: No Confidence Scoring

**Problem**: Can't distinguish high-confidence vs. uncertain extractions.

**Solution**: Include confidence metadata:
```python
chunk.confidence = 0.98  # Docling extraction confidence
chunk.metadata["extraction_confidence"] = 0.98
```

### Pitfall 5: Hallucinating Beyond Source

**Problem**: LLM invents ingredients not in document.

**Solution**: Use table structure + verification:
```python
# Table explicitly shows what IS vegan
# LLM cannot invent "X is vegan" if X not in table
# Because structure constrains possibilities
```

## Performance Optimization

### Chunking Strategy

```python
# Small chunks for precise citations
processor = DocumentProcessor(chunk_size=512, chunk_overlap=64)

# Larger chunks for context
processor = DocumentProcessor(chunk_size=2048, chunk_overlap=256)

# Balanced (recommended)
processor = DocumentProcessor(chunk_size=1024, chunk_overlap=128)
```

### Metadata Indexing

```python
# Create index for fast lookups
index = VectorDBFormatter.create_metadata_index(chunked)

# Fast retrieval by page
chunks_p5 = index["by_page"][5]  # O(1) lookup

# Fast table search
table_chunks = index["tables"]  # Pre-computed list
```

### Vector DB Selection

| DB | Best For | Trade-offs |
|---|---|---|
| **Chroma** | Development, local | Simple, in-memory |
| **Pinecone** | Production, scale | Cloud-based, cost |
| **Weaviate** | Graph queries | Complex setup |

## Testing & Validation

### Test Table Preservation

```python
def test_table_preservation():
    """Ensure tables survive chunking."""
    
    # Create table chunk
    chunk = TableAwareChunk(
        content=table_markdown,
        is_table=True,
    )
    
    # Verify structure
    assert "|" in chunk.content
    lines = chunk.content.split('\n')
    assert all('|' in line for line in lines)
    
    # Verify data integrity
    for row_data in expected_rows:
        assert row_data in chunk.content
```

### Test Citation Accuracy

```python
def test_citation_accuracy():
    """Ensure citations are specific and accurate."""
    
    chunk = TableAwareChunk(
        source_document="Guide.pdf",
        page_number=15,
        table_title="My Table",
    )
    
    citation = RAGCitationBuilder.create_citation(chunk)
    
    # Verify all info is in citation
    assert "Guide.pdf" in citation
    assert "p. 15" in citation or "p.15" in citation
    assert "My Table" in citation
```

### Test Grounding Verification

```python
def test_grounding_verification():
    """Ensure responses don't hallucinate."""
    
    chunks = [
        TableAwareChunk(content="Honey is from bees"),
        TableAwareChunk(content="Agave is from plants"),
    ]
    
    # Good response (grounded)
    good_response = "Honey is from bees."
    assert verify_grounding(good_response, chunks)
    
    # Bad response (hallucinated)
    bad_response = "Almonds are produced by bees."
    assert not verify_grounding(bad_response, chunks)
```

## Monitoring & Observability

### Log Key Metrics

```python
logging.info(f"Parsed {len(chunks)} chunks from {source}")
logging.info(f"Table chunks: {len(table_chunks)}")
logging.info(f"Avg confidence: {sum(c.confidence for c in chunks) / len(chunks):.2f}")
logging.info(f"Citation coverage: {len(cited_chunks)} / {len(chunks)}")
```

### Track Hallucinations

```python
def track_hallucination(response, chunks):
    """Log hallucination attempts."""
    verification = verify_response_grounding(response, chunks)
    
    if not verification["grounded"]:
        logging.warning(f"Hallucination detected: {verification['issues']}")
        # Send alert
```

## Production Checklist

- [ ] All tables preserve Markdown structure
- [ ] Every chunk has metadata (source, page, section)
- [ ] Citations use specific references
- [ ] Responses verified for grounding
- [ ] Confidence scores tracked
- [ ] Error handling for parse failures
- [ ] Logging and monitoring in place
- [ ] Tests for table preservation
- [ ] Tests for citation accuracy
- [ ] Tests for hallucination detection

## References

- [Docling Documentation](https://github.com/IBM/docling)
- [Markdown Tables](https://www.markdownguide.org/extended-syntax/#tables)
- [RAG Best Practices](https://docs.llamaindex.ai/en/latest/)
- [Hallucination Detection](https://arxiv.org/abs/2309.01431)
