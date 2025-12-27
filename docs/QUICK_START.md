# Quick Start Guide

Get started analyzing documents in 5 minutes!

## Installation

```bash
# Clone the repository
git clone https://github.com/MrRemit/intel-doc-analyzer.git
cd intel-doc-analyzer

# Install Python dependencies
pip install -r requirements.txt

# Set up your Anthropic API key
export ANTHROPIC_API_KEY="your_api_key_here"

# Or add to .env file
echo "ANTHROPIC_API_KEY=your_key" > .env
```

## Basic Usage

### 1. Analyze a Single Document

```bash
# Analyze a PDF file
python src/cli.py analyze my_document.pdf

# This will:
# - Extract text from PDF
# - Use Claude AI to extract entities (people, organizations, locations)
# - Build a knowledge graph
# - Save to data/graphs/analysis.graphml
# - Create visualization PNG
```

### 2. Analyze Multiple Documents

```bash
# Process an entire directory
mkdir -p data/raw
cp /path/to/documents/*.pdf data/raw/

python src/cli.py analyze data/raw/ --output my_investigation

# Results saved to:
# - data/graphs/my_investigation.graphml (graph data)
# - data/graphs/my_investigation.png (visualization)
```

### 3. Find Connections Between Entities

```bash
# Find shortest path (6 degrees of separation)
python src/cli.py query data/graphs/my_investigation.graphml "John Smith" "ACME Corporation"

# Output:
# 1. [PERSON] John Smith
#    ↓ works_at
# 2. [ORGANIZATION] Tech Startup Inc
#    ↓ acquired_by
# 3. [ORGANIZATION] ACME Corporation
```

### 4. Find Most Important Entities

```bash
# Rank by centrality (importance in network)
python src/cli.py centrality data/graphs/my_investigation.graphml --top 20

# Shows top 20 most connected/influential entities
```

### 5. Detect Communities

```bash
# Find clusters of related entities
python src/cli.py communities data/graphs/my_investigation.graphml

# Output:
# Community 1 (45 members):
#  - [ORGANIZATION] ACME Corp
#  - [PERSON] John Smith
#  - [PERSON] Jane Doe
#  ...
```

## Advanced Options

### Custom Analysis Parameters

```bash
python src/cli.py analyze documents/ \\
    --output investigation_2024 \\
    --model claude-opus-4-5-20251101 \\
    --confidence 0.8 \\
    --chunk-size 3000 \\
    --format graphml
```

**Options:**
- `--model`: Claude model (default: claude-opus-4-5-20251101)
- `--confidence`: Minimum confidence threshold 0-1 (default: 0.7)
- `--chunk-size`: Max characters per chunk (default: 4000)
- `--format`: Output format - graphml, gexf, or json (default: graphml)

### Visualization Layouts

```bash
python src/cli.py visualize graph.graphml \\
    --layout spring \\
    --output my_viz.png
```

**Layouts:**
- `spring`: Force-directed (default, best for most graphs)
- `circular`: Entities arranged in circle
- `kamada_kawai`: Energy-minimization layout

## Python API Usage

For more control, use the Python API directly:

```python
from src.ingestion.document_processor import DocumentProcessor
from src.extraction.entity_extractor import EntityExtractor
from src.graph.graph_builder import GraphBuilder

# 1. Process document
processor = DocumentProcessor()
chunks, metadata = processor.process_file("document.pdf")

# 2. Extract entities
extractor = EntityExtractor(api_key="your_key")
entities, relationships = extractor.extract_from_document(chunks, metadata.to_dict())

# 3. Build graph
builder = GraphBuilder("my_analysis")
for entity in entities:
    builder.add_entity(entity.to_dict())
for rel in relationships:
    builder.add_relationship(rel.to_dict())

# 4. Analyze
path = builder.shortest_path("Entity 1", "Entity 2")
centrality = builder.calculate_centrality()
communities = builder.detect_communities()

# 5. Save
builder.save("output.graphml")
builder.visualize("output.png")
```

## Supported File Formats

- **PDF**: Text extraction (PyMuPDF, pdfplumber)
- **DOCX**: Microsoft Word documents
- **TXT**: Plain text files
- **EML**: Email messages

## Entity Types Extracted

- `PERSON`: Individuals
- `ORGANIZATION`: Companies, agencies, groups
- `LOCATION`: Cities, countries, addresses
- `EVENT`: Meetings, incidents, conferences
- `DATE`: Specific dates or ranges
- `DOCUMENT`: Referenced documents
- `PHONE`: Phone numbers
- `EMAIL`: Email addresses
- `MONEY`: Financial amounts
- `LEGAL`: Case numbers, statutes

## Relationship Types

- `works_at`, `employed_by`
- `located_in`, `based_in`
- `attended`, `participated_in`
- `mentioned_in`
- `associated_with`
- `owns`, `controls`
- `transacted_with`
- `communicated_with`

## Tips for Best Results

### 1. Document Quality
- Use high-quality scanned PDFs (or OCR first with Tesseract)
- Clean, well-formatted documents work best
- Avoid heavily redacted documents

### 2. API Usage
- Start with small batches (5-10 documents)
- Monitor API usage and costs
- Use appropriate confidence thresholds (0.7-0.8 recommended)

### 3. Graph Analysis
- Merge duplicate entities manually if needed
- Use centrality to find key entities
- Communities help identify clusters (e.g., business networks, social circles)

### 4. Performance
- Larger chunk sizes = fewer API calls but less precision
- Smaller chunks = more API calls but better entity extraction
- Default 4000 chars is a good balance

## Troubleshooting

### "API key not set"
```bash
export ANTHROPIC_API_KEY="your_key"
# Or create .env file
```

### "No supported files found"
Ensure your files have supported extensions: .pdf, .docx, .txt, .eml

### "Rate limit hit"
The tool has automatic retry with exponential backoff. If you hit limits:
- Process fewer documents at once
- Increase delay between API calls
- Upgrade your Anthropic API tier

### "Graph visualization fails"
Requires matplotlib. Install with:
```bash
pip install matplotlib
```

### "Memory error on large documents"
- Reduce chunk size: `--chunk-size 2000`
- Process documents individually instead of batch
- Use more powerful machine or cloud instance

## Next Steps

1. **Web Interface** (coming in v1.0)
   - Interactive graph exploration
   - Click-to-expand entities
   - Filtering and search

2. **Neo4j Integration** (coming in v1.0)
   - Production-grade graph database
   - Better performance for large datasets
   - Advanced query capabilities

3. **OCR Support** (coming in v2.0)
   - Scanned document analysis
   - Tesseract integration

## Getting Help

- **Documentation**: See [README.md](../README.md)
- **Architecture**: See [CLAUDE.md](../CLAUDE.md)
- **Issues**: [GitHub Issues](https://github.com/MrRemit/intel-doc-analyzer/issues)
- **Examples**: Check `/docs/examples/`

## Example Use Cases

### Investigative Journalism
```bash
# Analyze leaked corporate emails
python src/cli.py analyze corporate_leaks/*.eml --output leak_investigation

# Find connections between executives
python src/cli.py query leak_investigation.graphml "CEO Name" "Shell Company"
```

### Academic Research
```bash
# Analyze historical document archive
python src/cli.py analyze jfk_files/ --output jfk_analysis

# Detect communities in social network
python src/cli.py communities jfk_analysis.graphml
```

### Legal Discovery
```bash
# Process case files
python src/cli.py analyze case_documents/*.pdf --confidence 0.8

# Find most mentioned entities
python src/cli.py centrality case.graphml --algorithm betweenness
```

---

**Happy analyzing!** 🔍
