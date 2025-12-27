# Intelligence Document Analyzer - Project Context

## Project Vision

**Problem**: Government and corporate document dumps (Epstein files, JFK files, FOIA releases) are dumped as thousands of unstructured PDFs. Journalists and researchers spend months manually reading and connecting dots.

**Solution**: AI-powered document analysis tool that automatically:
1. Ingests massive document dumps (PDFs, emails, scans)
2. Extracts entities (people, organizations, locations, events, dates)
3. Maps relationships between entities
4. Builds interactive knowledge graph visualization (Maltego-style)
5. Enables 6-degrees-of-separation exploration

## Architecture Overview

```
Document Dumps (PDFs, emails, scans)
    ↓
[1] INGESTION MODULE
    - PDF parsing (PyMuPDF, pdfplumber)
    - Email parsing (email, mailbox)
    - OCR for scanned documents (Tesseract)
    - Text chunking for large documents
    ↓
[2] AI EXTRACTION ENGINE (Claude API)
    - Named Entity Recognition (NER)
    - Relationship extraction
    - Coreference resolution
    - Confidence scoring
    ↓
[3] GRAPH DATABASE
    - Entity nodes (Person, Organization, Location, Document, Event)
    - Relationship edges (works_at, located_in, mentioned_in, connected_to)
    - Metadata (dates, confidence scores, source documents)
    - Deduplication and entity merging
    ↓
[4] VISUALIZATION LAYER
    - Interactive network graph (Cytoscape.js, vis.js, or D3.js)
    - Click-to-explore interface
    - Filtering (by entity type, date range, confidence)
    - Path finding (shortest connection between entities)
    - Export capabilities (PDF reports, JSON data)
```

## Tech Stack

### Backend (Python)
- **Document Processing**: PyMuPDF, pdfplumber, python-docx, email
- **OCR**: pytesseract, pdf2image
- **AI/NLP**: anthropic SDK (Claude API), langchain (optional)
- **Graph Database**: NetworkX (simple), Neo4j (production), or ArangoDB
- **API Framework**: FastAPI
- **Data Validation**: pydantic

### Frontend (Web)
- **Framework**: React + TypeScript or vanilla JS
- **Graph Visualization**: Cytoscape.js, vis-network, or D3.js force-directed
- **UI**: Tailwind CSS or Bootstrap
- **State**: React Context or Zustand

### Infrastructure
- **Containerization**: Docker (optional)
- **Storage**: Local filesystem + SQLite/PostgreSQL for metadata
- **Cache**: Redis (for processed documents)

## Data Models

### Entity Schema
```python
{
    "id": "e_12345",                    # Unique identifier
    "type": "PERSON|ORGANIZATION|LOCATION|DOCUMENT|EVENT|DATE",
    "text": "John Smith",               # As appears in document
    "canonical_name": "John Smith",     # Normalized/merged name
    "confidence": 0.95,                 # 0-1 extraction confidence
    "source_documents": ["doc1.pdf"],   # Where entity was found
    "mentions": 15,                     # Number of times mentioned
    "metadata": {
        "aliases": ["J. Smith"],
        "first_seen": "2024-01-15",
        "attributes": {...}             # Type-specific data
    }
}
```

### Relationship Schema
```python
{
    "id": "r_67890",
    "source_id": "e_12345",             # Source entity
    "target_id": "e_54321",             # Target entity
    "relationship_type": "works_at|located_in|mentioned_in|associated_with",
    "confidence": 0.88,
    "evidence": "John Smith is CEO of ACME Corp",  # Supporting text
    "source_document": "doc1.pdf",
    "page_number": 5,
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### Document Schema
```python
{
    "id": "doc_001",
    "filename": "epstein_flight_logs.pdf",
    "file_type": "pdf",
    "pages": 47,
    "processed_date": "2024-01-15",
    "status": "completed|processing|failed",
    "entities_extracted": 234,
    "relationships_extracted": 567,
    "metadata": {
        "author": "...",
        "creation_date": "...",
        "source": "FOIA request #..."
    }
}
```

## Entity Types Taxonomy

### Core Entity Types
- **PERSON**: Individuals mentioned in documents
- **ORGANIZATION**: Companies, agencies, groups
- **LOCATION**: Cities, countries, addresses, facilities
- **DOCUMENT**: Referenced documents, files, reports
- **EVENT**: Meetings, transactions, incidents
- **DATE**: Specific dates or date ranges
- **PHONE**: Phone numbers
- **EMAIL**: Email addresses
- **MONEY**: Financial amounts
- **LEGAL**: Case numbers, statutes, regulations

### Relationship Types
- **direct**: Explicit relationships stated in text
- **inferred**: Relationships derived from context
- **temporal**: Time-based connections
- **spatial**: Location-based connections
- **document**: Co-occurrence in same document

## Processing Pipeline

### Phase 1: Ingestion
```
Input: /data/raw/*.pdf
Process:
  1. Extract text from PDF (preserve page numbers)
  2. Chunk into processable segments (max 4000 tokens)
  3. Store chunks with metadata
Output: /data/processed/{doc_id}/chunks.json
```

### Phase 2: Entity Extraction
```
Input: Document chunks
Process:
  1. Send chunk to Claude API with extraction prompt
  2. Parse JSON response (entities + relationships)
  3. Validate schema and confidence thresholds
  4. Deduplicate entities within document
Output: /data/processed/{doc_id}/entities.json
```

### Phase 3: Graph Building
```
Input: All extracted entities + relationships
Process:
  1. Merge duplicate entities across documents
  2. Build graph structure (nodes + edges)
  3. Calculate entity importance (PageRank, centrality)
  4. Identify communities/clusters
Output: /data/graphs/{dataset_name}.graphml
```

### Phase 4: Visualization
```
Input: Graph database
Process:
  1. Serve API endpoints (GET entities, relationships, subgraphs)
  2. Frontend fetches initial graph or query results
  3. Interactive exploration (click node → expand neighbors)
  4. Export views (PNG, PDF, JSON)
```

## Claude API Integration

### Entity Extraction Prompt Template
```python
system_prompt = """You are an expert document analyst. Extract all named entities and their relationships from the provided text.

Entity Types: PERSON, ORGANIZATION, LOCATION, EVENT, DATE, DOCUMENT, PHONE, EMAIL, MONEY

For each entity, provide:
- Unique ID
- Type
- Text as it appears
- Confidence score (0-1)

For each relationship:
- Source entity ID
- Target entity ID
- Relationship type
- Confidence score
- Supporting evidence (exact quote)

Output ONLY valid JSON. No markdown, no explanations."""

user_prompt = f"""Document: {document_name}
Page: {page_num}

Text:
{chunk_text}

Extract entities and relationships:"""
```

### Response Validation
- Verify JSON structure
- Check confidence thresholds (default: 0.7 minimum)
- Validate entity IDs are unique
- Ensure relationship source/target IDs exist
- Sanitize text for special characters

## Configuration & Settings

### Confidence Thresholds
- **High confidence**: >= 0.9 (use directly)
- **Medium confidence**: 0.7-0.9 (flag for review)
- **Low confidence**: < 0.7 (discard or manual review)

### Processing Limits
- **Max chunk size**: 4000 tokens (~3000 words)
- **Max entities per chunk**: 100
- **Max relationships per chunk**: 200
- **API rate limit**: 50 requests/minute (Claude API tier-dependent)

### File Handling
- **Supported formats**: PDF, DOCX, TXT, EML, MBOX
- **Max file size**: 100MB per document
- **Batch size**: 10 documents concurrent processing

## Development Phases

### MVP (Minimum Viable Product)
- [x] Project structure
- [ ] PDF ingestion (basic text extraction)
- [ ] Claude API entity extraction (PERSON, ORGANIZATION only)
- [ ] Simple graph storage (NetworkX)
- [ ] Basic web visualization (Cytoscape.js)
- [ ] CLI interface

### v1.0 (Production Ready)
- [ ] All document formats (PDF, DOCX, EML, MBOX)
- [ ] All entity types
- [ ] Neo4j graph database
- [ ] Advanced visualization (filtering, search, export)
- [ ] Web API (FastAPI)
- [ ] Docker deployment

### v2.0 (Advanced Features)
- [ ] OCR for scanned documents
- [ ] Coreference resolution
- [ ] Temporal analysis (timeline view)
- [ ] Entity disambiguation (link to external databases)
- [ ] Collaborative annotation
- [ ] Multi-language support

## Commands & Conventions

### File Naming
- Source code: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`
- Constants: `UPPER_SNAKE_CASE`

### Git Workflow
- Feature branches: `feature/entity-extraction`
- Bugfix branches: `bugfix/pdf-parsing-error`
- Commit messages: Imperative mood ("Add entity extraction" not "Added")

### Testing
- Unit tests: `pytest tests/`
- Test coverage: Minimum 70%
- Integration tests for full pipeline

### Documentation
- Docstrings: Google style
- API docs: Auto-generated with FastAPI
- User guide: Markdown in `/docs`

## Key Design Decisions

1. **Why NetworkX for MVP, Neo4j for production?**
   - NetworkX: Fast prototyping, no database setup, good for small datasets
   - Neo4j: Scalable, optimized graph queries, production-grade

2. **Why Claude API instead of local NER models?**
   - Better accuracy for complex entity types
   - Relationship extraction is hard for traditional NER
   - Contextual understanding (coreference, implied relationships)

3. **Why chunk documents instead of full-text processing?**
   - Claude API token limits
   - Better context focus per chunk
   - Parallel processing capabilities

4. **Why web visualization instead of desktop app?**
   - Cross-platform compatibility
   - Easier deployment and sharing
   - Collaborative features possible

## Security & Privacy

### Sensitive Data Handling
- **DO NOT commit**: Original documents, API keys, extracted personal data
- **Anonymize**: Option to redact PII before visualization
- **Access control**: Authentication for web interface (v1.0+)
- **Audit log**: Track who accessed what entities/documents

### .gitignore Critical Items
```
# Sensitive data
/data/raw/**
/data/processed/**
*.pdf
*.docx
*.eml

# Credentials
.env
config/secrets.json
anthropic_api_key.txt

# Large files
*.graphml
*.db
*.sqlite
```

## Current Status

**Last Updated**: 2024-12-27
**Phase**: Project initialization
**Next Steps**:
1. Create requirements.txt with core dependencies
2. Implement PDF ingestion module
3. Build entity extraction with Claude API
4. Test on sample document (10-page PDF)

## Notes & Ideas

- Consider using LangChain for Claude API abstraction (easier prompt management)
- Explore Hugging Face transformers for supplementary NER (speed vs accuracy trade-off)
- Add export to Gephi format for advanced network analysis
- Potential integration with Palantir Gotham-style timeline views
- Community detection algorithms: Louvain, Label Propagation
- Consider graph embeddings (Node2Vec) for ML-based entity similarity
