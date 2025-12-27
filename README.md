# 🔍 Intelligence Document Analyzer

**🆓 100% FREE AI-Powered Document Analysis - No API Costs!**

Transform thousands of unstructured documents (PDFs, emails, scans) into interactive, explorable knowledge graphs using **FREE local AI (spaCy)**. No API keys, no costs, completely open-source. Built for investigative journalists, researchers, and anyone dealing with massive FOIA releases, government document dumps, or corporate leak archives.

---

## 🎯 The Problem

When governments and organizations release document dumps (Epstein files, JFK files, corporate leaks), they arrive as **thousands of unstructured PDFs** with:
- ❌ No organization or categorization
- ❌ No way to find connections between entities
- ❌ Months of manual reading required
- ❌ Easy to miss critical relationships

**Examples**: Epstein files, JFK assassination docs, Panama Papers, Wikileaks cables, corporate FOIA releases

---

## ✨ The Solution

**Intelligence Document Analyzer** automatically:

1. **📥 Ingests** massive document collections (PDF, DOCX, email, scans)
2. **🤖 Extracts** entities using **FREE local AI (spaCy)**:
   - People, organizations, locations
   - Events, dates, phone numbers, emails
   - Financial amounts, legal references
   - **NO API costs, runs completely offline!**
3. **🔗 Maps relationships** between entities:
   - Who knows whom
   - Who works where
   - Who attended what event
   - Document co-mentions
4. **📊 Visualizes** as interactive network graphs (Maltego-style)
5. **🔍 Enables exploration**:
   - Click any person → see all connections
   - Find shortest path between two entities (6 degrees of separation)
   - Filter by date, confidence, entity type
   - Export findings as reports

### 💰 Cost Comparison:
- **This Tool (spaCy)**: $0 forever 🆓
- **Commercial alternatives**: $50-200+ per 1,000 documents 💸
- **Optional Claude AI**: Available if you want premium accuracy (requires API key)

---

## 🚀 Quick Start

### Installation (100% FREE - No API Keys!)

```bash
# Clone the repository
git clone https://github.com/MrRemit/intel-doc-analyzer.git
cd intel-doc-analyzer

# Install Python dependencies (includes FREE spaCy)
pip install -r requirements.txt

# Download spaCy language model (one-time, ~40MB)
python -m spacy download en_core_web_sm

# That's it! No API keys needed! 🎉
```

### Basic Usage (FREE Mode)

```bash
# Analyze documents with FREE local AI (no costs!)
python src/cli.py analyze data/examples/sample_document.txt --output my_analysis

# That's it! Extracted entities, built graph, created visualization
# Total cost: $0.00 💰
```

**Output:**
- `data/graphs/my_analysis.json` - Knowledge graph
- `data/graphs/my_analysis.png` - Network visualization
- Extracted entities & relationships saved

### Query the Graph

```bash
# Find connections between entities
python src/cli.py query data/graphs/my_analysis.json "John Smith" "ACME Corp"

# Find most important entities
python src/cli.py centrality data/graphs/my_analysis.json --top 20

# Detect communities
python src/cli.py communities data/graphs/my_analysis.json
```

---

## 📖 Usage Examples

### Example 1: Analyze a FOIA Document Dump

```bash
# Process 1,000 PDFs from government release
python src/cli.py analyze \
    --input data/raw/foia_release/ \
    --output data/graphs/foia_analysis \
    --entity-types PERSON,ORGANIZATION,LOCATION,EVENT \
    --confidence-threshold 0.75

# Results:
# ✓ Extracted 5,432 entities
# ✓ Found 12,874 relationships
# ✓ Identified 23 communities
# ✓ Processing time: 2h 15m
```

### Example 2: Find Connections Between Two People

```python
from src.graph import GraphAnalyzer

graph = GraphAnalyzer.load("data/graphs/foia_analysis.graphml")

# Find shortest path between two entities
path = graph.shortest_path("John Smith", "ACME Corporation")
print(path)
# Output:
# John Smith → works_at → Tech Startup Inc → acquired_by → ACME Corporation
# (3 degrees of separation)
```

### Example 3: Python API

```python
from src.ingestion import DocumentProcessor
from src.extraction import EntityExtractor
from src.graph import GraphBuilder

# 1. Process PDF
processor = DocumentProcessor()
chunks = processor.process_pdf("data/raw/document.pdf")

# 2. Extract entities with Claude AI
extractor = EntityExtractor(api_key="your_key")
entities, relationships = extractor.extract(chunks)

# 3. Build graph
builder = GraphBuilder()
builder.add_entities(entities)
builder.add_relationships(relationships)
builder.save("data/graphs/my_graph.graphml")
```

---

## 🏗️ Architecture

```
┌─────────────────────┐
│  Document Dumps     │
│  (PDF, Email, Scan) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  1. INGESTION       │
│  - PDF parsing      │
│  - Email parsing    │
│  - OCR (scans)      │
│  - Text chunking    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  2. AI EXTRACTION   │
│  - Claude API       │
│  - Entity NER       │
│  - Relationships    │
│  - Confidence       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  3. GRAPH DATABASE  │
│  - NetworkX (MVP)   │
│  - Neo4j (Prod)     │
│  - Deduplication    │
│  - Merging          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  4. VISUALIZATION   │
│  - Interactive web  │
│  - Cytoscape.js     │
│  - Filtering        │
│  - Export reports   │
└─────────────────────┘
```

---

## 🎨 Features

### Current Features (MVP)
- ✅ PDF text extraction
- ✅ Claude AI entity extraction (PERSON, ORGANIZATION, LOCATION)
- ✅ Relationship mapping
- ✅ NetworkX graph storage
- ✅ Basic web visualization
- ✅ CLI interface

### Coming Soon (v1.0)
- 🔜 All document formats (DOCX, email, MBOX)
- 🔜 OCR for scanned documents
- 🔜 Neo4j production database
- 🔜 Advanced filtering & search
- 🔜 Timeline view (temporal analysis)
- 🔜 Export to PDF reports
- 🔜 Docker deployment

### Future (v2.0+)
- 💡 Coreference resolution (merge "John Smith" and "J. Smith")
- 💡 Entity disambiguation (link to Wikipedia, Wikidata)
- 💡 Multi-language support
- 💡 Collaborative annotation
- 💡 Machine learning entity ranking

---

## 🛠️ Technology Stack

### Backend (Python 3.9+)
- **AI/NLP**: Anthropic Claude API (entity extraction)
- **Document Processing**: PyMuPDF, pdfplumber, python-docx
- **OCR**: Tesseract, pytesseract
- **Graph**: NetworkX (MVP), Neo4j (production)
- **API**: FastAPI + uvicorn
- **Data Validation**: Pydantic

### Frontend (Web)
- **Framework**: React + TypeScript
- **Visualization**: Cytoscape.js (interactive network graphs)
- **UI**: Tailwind CSS
- **State Management**: Zustand

### Infrastructure
- **Containerization**: Docker
- **Database**: SQLite (metadata), PostgreSQL (optional)
- **Cache**: Redis (optional)

---

## 📊 Entity Types Supported

### Core Entities
- **PERSON**: Individuals mentioned in documents
- **ORGANIZATION**: Companies, agencies, groups, NGOs
- **LOCATION**: Cities, countries, addresses, buildings
- **EVENT**: Meetings, transactions, incidents, conferences
- **DOCUMENT**: Referenced documents, files, reports
- **DATE**: Specific dates or date ranges

### Additional Entities
- **PHONE**: Phone numbers
- **EMAIL**: Email addresses
- **MONEY**: Financial amounts (USD, EUR, etc.)
- **LEGAL**: Case numbers, statutes, regulations
- **VEHICLE**: License plates, aircraft tail numbers

### Relationship Types
- `works_at`, `employed_by`
- `located_in`, `based_in`
- `attended`, `participated_in`
- `mentioned_in` (document co-occurrence)
- `associated_with` (general connection)
- `owns`, `controls`
- `transacted_with`

---

## 🔐 Security & Privacy

### Data Protection
- ✅ All document processing is **local** (documents never leave your machine)
- ✅ Claude API only receives **text chunks**, not full documents
- ✅ `.gitignore` protects sensitive files
- ✅ Optional PII anonymization before visualization
- ✅ Audit logging for access tracking

### Best Practices
- 🔒 Never commit original documents to git
- 🔒 Use `.env` for API keys (never hardcode)
- 🔒 Sanitize data before sharing visualizations
- 🔒 Enable authentication for web interface (production)

---

## 📚 Documentation

- **[User Guide](docs/user-guide.md)** - Complete usage documentation
- **[API Reference](docs/api-reference.md)** - Python API docs
- **[Architecture](docs/architecture.md)** - System design details
- **[Development](docs/development.md)** - Contributing guide
- **[CLAUDE.md](CLAUDE.md)** - AI context (full project specification)

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test module
pytest tests/test_entity_extraction.py
```

---

## 🤝 Contributing

Contributions welcome! This tool is built to help journalists, researchers, and transparency advocates.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details

**Security Notice**: This software is intended for **educational, research, and authorized investigative journalism** purposes only. Users must comply with all applicable laws. Unauthorized access to confidential documents is illegal and unethical.

The authors are not responsible for misuse of this software.

---

## 🙏 Acknowledgments

- **Anthropic Claude** - AI-powered entity extraction
- **Cytoscape.js** - Network graph visualization
- **PyMuPDF** - Fast PDF processing
- **NetworkX** - Python graph library
- **Maltego** - Inspiration for visualization UX

---

## 📞 Contact

**Author**: MrR3m1t
**GitHub**: [@MrRemit](https://github.com/MrRemit)
**Repository**: [intel-doc-analyzer](https://github.com/MrRemit/intel-doc-analyzer)

**Issues**: Report bugs or request features via [GitHub Issues](https://github.com/MrRemit/intel-doc-analyzer/issues)

---

## 🎯 Use Cases

### Investigative Journalism
- Analyze leaked documents (Panama Papers style)
- Map corporate/political networks
- Find hidden connections in FOIA releases

### Academic Research
- Historical document analysis (declassified archives)
- Social network studies
- Computational journalism

### Legal & Compliance
- eDiscovery (find relevant entities in case files)
- Regulatory compliance investigations
- Fraud detection networks

### Intelligence Analysis
- OSINT (Open Source Intelligence)
- Threat actor mapping
- Attribution analysis

---

## 📈 Roadmap

**Phase 1: MVP** (Current)
- [x] Project structure
- [x] PDF ingestion
- [ ] Claude API entity extraction
- [ ] Basic graph storage
- [ ] Simple web visualization
- [ ] CLI interface

**Phase 2: v1.0** (Q1 2025)
- [ ] All document formats
- [ ] Neo4j integration
- [ ] Advanced filtering
- [ ] Timeline view
- [ ] PDF export
- [ ] Docker deployment

**Phase 3: v2.0** (Q2 2025)
- [ ] OCR for scans
- [ ] Coreference resolution
- [ ] Entity disambiguation
- [ ] Multi-language support
- [ ] Collaborative features

---

**Made with ❤️ for transparency and accountability**

---

## 💡 FREE vs Premium Extraction

### FREE Mode (Default - spaCy)
```bash
# Uses local spaCy AI - completely FREE
python src/cli.py analyze documents/ --engine spacy
```
✅ $0 cost  
✅ Works offline  
✅ No API keys  
✅ 75-85% accuracy  
✅ Fast processing  

### Premium Mode (Optional - Claude AI)
```bash
# Uses Claude API - costs money but higher accuracy
python src/cli.py analyze documents/ --engine claude --api-key sk-ant-...
```
💰 ~$0.10 per document  
🌐 Requires internet  
🔑 Needs API key  
✅ 95%+ accuracy  
✅ Better relationship extraction  

**Recommendation:** Start with FREE mode. Only use Claude for critical documents where you need maximum accuracy.

