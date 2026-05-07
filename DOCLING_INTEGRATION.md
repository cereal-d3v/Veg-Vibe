# High-Fidelity Document Parsing with Docling

## Overview

Veg-Vibe now integrates **Docling** for high-fidelity PDF parsing with special emphasis on table preservation and metadata extraction. This enables:

- 📊 **Table-Aware Chunking**: Preserves table structures in Markdown
- 📄 **Metadata Extraction**: Pages, sections, headings, tables
- 🔗 **Precise Citations**: "According to Table 1 in PETA Guide (p. 15)"
- 🛡️ **Hallucination Prevention**: Structured data prevents invention
- 🔄 **Vector DB Integration**: Ready for Chroma, Pinecone, Weaviate

## Architecture

### Data Flow

```
PDF Input
   ↓
Docling DocumentConverter
   ↓
Markdown Output (Preserves Structure)
   ↓
TableAwareChunking (Splits by page, section, table)
   ↓
Metadata Extraction (Page #, Section, Table Title)
   ↓
ChunkedDocument (Container with Citations)
   ↓
VectorDB Compatibility Layer
   ↓
Vector Database (Chroma/Pinecone/Weaviate)
   ↓
DocumentAwareAssistant (RAG with Source Attribution)
```

### Core Components

#### 1. DocumentProcessor (`app/ingestion/docling_parser.py`)

Main entry point for document parsing:

```python
from app.ingestion import DocumentProcessor

processor = DocumentProcessor(chunk_size=1024, chunk_overlap=128)
chunked_doc = processor.parse_document("path/to/PETA_Guide.pdf")

print(f"Parsed {len(chunked_doc.chunks)} chunks")
print(f"Total pages: {chunked_doc.total_pages}")
```

**Key Methods**:
- `parse_document(pdf_path)` → ChunkedDocument
- `_extract_chunks(doc, source_path)` → List[TableAwareChunk]
- `_create_chunk(...)` → TableAwareChunk
- `_extract_toc(doc)` → Dict (table of contents)

#### 2. TableAwareChunk Data Structure

Represents a single chunk with full metadata:

```python
@dataclass
class TableAwareChunk:
    id: str                    # Unique identifier (e.g., "doc_p5_c2")
    content: str               # Markdown content
    source_document: str       # Source PDF path
    page_number: int           # 1-indexed page
    section_heading: str       # Parent section
    is_table: bool             # True if table chunk
    table_title: str           # Table caption/title
    confidence: float          # 0-1 extraction confidence
    metadata: Dict             # Custom metadata
```

**Key Methods**:
- `to_embedding_text()` → str (text for embeddings)
- `to_citation_reference()` → str (citation string)
- `to_dict()` → Dict (for vector DB storage)

#### 3. ChunkedDocument Container

Represents fully parsed document:

```python
@dataclass
class ChunkedDocument:
    source_path: str           # Original PDF path
    document_title: str        # Extracted or inferred title
    total_pages: int
    chunks: List[TableAwareChunk]
    table_of_contents: Dict
    parsing_metadata: Dict
```

**Key Methods**:
- `to_dict()` → Dict
- `to_json(filepath)` → Save to JSON

#### 4. VectorDB Compatibility Layer (`app/ingestion/vectordb_compat.py`)

Convert chunks to database formats:

```python
from app.ingestion import VectorDBFormatter

# For Chroma
ids, documents, metadatas = VectorDBFormatter.to_chroma_documents(chunked_doc)

# For Pinecone (requires embeddings)
vectors = VectorDBFormatter.to_pinecone_vectors(chunked_doc, embeddings)

# For Weaviate
objects = VectorDBFormatter.to_weaviate_objects(chunked_doc)

# Create metadata index
index = VectorDBFormatter.create_metadata_index(chunked_doc)
# Returns: {"by_page": {}, "by_section": {}, "tables": []}
```

#### 5. RAG Citation Builder

Generate precise citations:

```python
from app.ingestion import RAGCitationBuilder

# Single citation
citation = RAGCitationBuilder.create_citation(chunk)
# Output: "PETA_Guide.pdf (p. 15), Section: Animal-Derived Products"

# Batch citations
citations = RAGCitationBuilder.create_citations_batch(chunks)

# Citation context for LLM
context = RAGCitationBuilder.create_citation_context(chunks, "Is honey vegan?")
# Output formatted with 📊 and 📄 emojis for tables/text
```

#### 6. DocumentAwareAssistant (Enhanced RAG)

Extended agentic assistant with document support:

```python
from app.ingestion import get_document_processor
from app.utils.agentic_rag import DocumentAwareAssistant
from app.utils.recommend import RecipeRecommender

# Initialize
processor = get_document_processor()
recommender = RecipeRecommender("recipes.csv")
assistant = DocumentAwareAssistant(recommender)

# Parse and add document chunks
chunked = processor.parse_document("PETA_Ingredient_Guide.pdf")
chunks_for_rag = [
    {
        "id": chunk.id,
        "content": chunk.content,
        "source": chunk.source_document,
        "page": chunk.page_number,
        "section": chunk.section_heading,
        "is_table": chunk.is_table,
        "table_title": chunk.table_title,
    }
    for chunk in chunked.chunks
]
assistant.add_document_chunks(chunks_for_rag)

# Generate answer with document attribution
response = assistant.answer_with_documents(
    "Is honey vegan?",
    include_document_sources=True
)

print(response["answer"])
# Includes: "According to Table 1 in PETA_Ingredient_Guide.pdf (p. 3)"
```

## Usage Examples

### Example 1: Parse PETA Ingredient Guide

```python
from app.ingestion import DocumentProcessor
import json

processor = DocumentProcessor()
result = processor.parse_document("PETA_Ingredient_Guide.pdf")

# Save to JSON for inspection
result.to_json("parsed_peta_guide.json")

# Access chunks
for chunk in result.chunks:
    if chunk.is_table:
        print(f"📊 Table on p. {chunk.page_number}: {chunk.table_title}")
        print(chunk.content)
    else:
        print(f"📄 Section '{chunk.section_heading}' on p. {chunk.page_number}")
```

### Example 2: Vector DB Integration with Chroma

```python
from app.ingestion import DocumentProcessor, VectorDBFormatter
import chromadb

# Parse document
processor = DocumentProcessor()
chunked = processor.parse_document("restaurant_menu.pdf")

# Convert to Chroma format
ids, documents, metadatas = VectorDBFormatter.to_chroma_documents(chunked)

# Add to Chroma collection
client = chromadb.Client()
collection = client.create_collection("restaurant_menus")
collection.add(ids=ids, documents=documents, metadatas=metadatas)

# Query
results = collection.query(query_texts=["vegan dishes"], n_results=5)
```

### Example 3: Citation-Aware RAG Response

```python
from app.ingestion import DocumentProcessor, RAGCitationBuilder

# Parse documents
processor = DocumentProcessor()
docs = []
for pdf in ["guide1.pdf", "guide2.pdf"]:
    chunked = processor.parse_document(pdf)
    docs.append(chunked)

# When generating response, use citations
from app.utils.agentic_rag import DocumentAwareAssistant

assistant = DocumentAwareAssistant(recommender)
for chunked in docs:
    chunks_data = [
        {
            "id": c.id,
            "content": c.content,
            "source": c.source_document,
            "page": c.page_number,
            "section": c.section_heading,
        }
        for c in chunked.chunks
    ]
    assistant.add_document_chunks(chunks_data)

response = assistant.answer_with_documents("vegan substitutes")
print(response["answer"])
# Includes precise citations like: "According to PETA Guide (p. 15)"
```

## Table Preservation

### Before Docling (Naive Chunking)

**Input PDF Table**:
```
| Ingredient | Vegan? | Notes         |
|------------|--------|---------------|
| Honey      | NO     | From bees     |
| Agave      | YES    | Plant-based   |
```

**Without Table Awareness**:
```
"ingredient vegan notes honey no from bees agave yes plant-based"
[STRUCTURE LOST - No way to retrieve specific cell values]
```

### With Docling (Table-Aware)

**Docling Output (Markdown)**:
```markdown
| Ingredient | Vegan? | Notes         |
|------------|--------|---------------|
| Honey      | NO     | From bees     |
| Agave      | YES    | Plant-based   |
```

**TableAwareChunk**:
```python
chunk = TableAwareChunk(
    id="doc_p5_table_1",
    content="[Full table in Markdown]",
    is_table=True,
    table_title="Ingredient Classification",
    page_number=5,
)
```

**Advantages**:
✅ Table structure preserved in Markdown
✅ Can query: "Which ingredients are vegan?"
✅ Can cite: "According to Table on p. 5"
✅ Prevents hallucination: LLM can't invent missing rows
✅ Allows table-specific confidence scoring

## Hallucination Prevention Strategy

### 1. **Structured Data Preservation**

Tables are preserved as Markdown with structure intact:

```python
# LLM sees this:
"""
| Ingredient | Status |
| --- | --- |
| Honey | Non-Vegan |
| Casein | Non-Vegan |
"""

# NOT:
# "honey casein are not vegan because they're from animals"
# (LLM could invent other non-vegan ingredients)
```

### 2. **Metadata Prevents False Attribution**

Each chunk has source information:

```python
chunk.metadata = {
    "source": "PETA_Official_Guide.pdf",
    "page": 3,
    "section": "Animal-Derived Ingredients",
    "extraction_confidence": 0.98,
}
# LLM cannot claim: "The PETA guide says X is vegan" (when it doesn't)
```

### 3. **Citation Requirements**

RAG pipeline requires specific citations:

```python
"According to Table 1 in PETA_Official_Guide.pdf (p. 3),
Honey is not vegan."
[Citation required - prevents "made-up source" claims]
```

### 4. **Verification Against Structured Data**

Grounding verification checks that outputs match source:

```python
def verify_grounding(response, chunks):
    # Ensure all mentioned ingredients exist in chunks
    # Ensure all facts are traceable to source
    # Flag hallucinated claims
```

## Testing

Run comprehensive test suite:

```bash
cd backend
pytest tests/test_parser.py -v

# Run specific test class
pytest tests/test_parser.py::TestDocumentProcessor -v

# Run with coverage
pytest tests/test_parser.py --cov=app.ingestion
```

**Test Coverage**:
- DocumentProcessor initialization and parsing
- TableAwareChunk creation and metadata
- Citation generation
- ChunkedDocument container
- VectorDB format conversions (Chroma, Pinecone, Weaviate)
- Metadata indexing
- Table preservation
- Real-world scenarios (PETA guides, menus)
- Regression tests (data integrity, no loss)

## API Reference

### DocumentProcessor

```python
class DocumentProcessor:
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 128)
    def parse_document(self, pdf_path: str) -> ChunkedDocument
    def _extract_chunks(doc, source_path) -> List[TableAwareChunk]
```

### TableAwareChunk

```python
@dataclass
class TableAwareChunk:
    id: str
    content: str
    source_document: str
    page_number: int
    section_heading: Optional[str]
    is_table: bool
    table_title: Optional[str]
    confidence: float
    metadata: Dict
    
    def to_embedding_text() -> str
    def to_citation_reference() -> str
    def to_dict() -> Dict
```

### ChunkedDocument

```python
@dataclass
class ChunkedDocument:
    source_path: str
    document_title: str
    total_pages: int
    chunks: List[TableAwareChunk]
    table_of_contents: Dict
    parsing_metadata: Dict
    
    def to_dict() -> Dict
    def to_json(filepath: Path) -> None
```

### VectorDBFormatter

```python
class VectorDBFormatter:
    @staticmethod
    def to_chroma_documents(chunked_doc) -> (ids, documents, metadatas)
    
    @staticmethod
    def to_pinecone_vectors(chunked_doc, embeddings) -> vectors
    
    @staticmethod
    def to_weaviate_objects(chunked_doc) -> objects
    
    @staticmethod
    def create_metadata_index(chunked_doc) -> index
```

### DocumentAwareAssistant

```python
class DocumentAwareAssistant(AgenticRecipeAssistant):
    def add_document_chunks(self, chunks: List[Dict]) -> None
    def answer_with_documents(
        self,
        question: str,
        max_results: int = 5,
        include_document_sources: bool = True
    ) -> Dict
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Parse small PDF (5 pages) | ~2-5s | Depends on complexity |
| Extract 100 chunks | ~0.5s | In-memory operation |
| Convert to Chroma | ~0.2s | Format conversion only |
| Vector DB query | ~50-200ms | Depends on DB size |
| Generate citation | ~10ms | Metadata lookup |

## Troubleshooting

### Issue: "DocumentConverter not found"

**Solution**: Ensure Docling is installed:
```bash
pip install docling==1.29.0 docling-core==1.3.0
```

### Issue: PDF parsing fails

**Solution**: Verify PDF is valid and not corrupted:
```python
try:
    result = processor.parse_document("file.pdf")
except Exception as e:
    print(f"Parse error: {e}")
    # Try alternative: convert to text first
```

### Issue: Tables become gibberish

**Solution**: This shouldn't happen with Docling - it preserves Markdown:
```python
# If tables appear corrupted, check:
assert "|" in chunk.content  # Markdown tables use |
assert chunk.is_table == True  # Should be marked as table
```

## Future Enhancements

- [ ] Support for multi-column layouts
- [ ] Figure/image extraction and captioning
- [ ] Handwriting recognition
- [ ] Automatic table-to-CSV export
- [ ] OCR for scanned PDFs
- [ ] Nested table support
- [ ] Chemical formula preservation
- [ ] Language detection and preservation

## References

- **Docling**: https://github.com/IBM/docling
- **Markdown Tables**: https://www.markdownguide.org/extended-syntax/#tables
- **Chroma**: https://www.trychroma.com/
- **Pinecone**: https://www.pinecone.io/
- **Weaviate**: https://weaviate.io/
