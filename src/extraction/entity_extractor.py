"""
AI Entity Extraction Engine - Claude API Integration

Extracts named entities and relationships from document chunks using Claude AI.
"""

import anthropic
import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import time
from datetime import datetime


@dataclass
class Entity:
    """Represents an extracted entity"""
    id: str
    type: str  # PERSON, ORGANIZATION, LOCATION, EVENT, DATE, etc.
    text: str  # As it appears in document
    confidence: float  # 0-1 score
    source_document: str
    source_chunk: str
    page_number: Optional[int] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items()}


@dataclass
class Relationship:
    """Represents a relationship between two entities"""
    id: str
    source_id: str  # Source entity ID
    target_id: str  # Target entity ID
    relationship_type: str  # works_at, located_in, mentioned_in, etc.
    confidence: float
    evidence: str  # Supporting text quote
    source_document: str
    source_chunk: str
    page_number: Optional[int] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items()}


class EntityExtractor:
    """
    Extract entities and relationships using Claude AI

    Features:
    - Named Entity Recognition (PERSON, ORGANIZATION, LOCATION, EVENT, DATE, etc.)
    - Relationship extraction between entities
    - Confidence scoring
    - Automatic retry with exponential backoff
    - Batch processing support
    - JSON validation
    """

    # Entity types to extract
    ENTITY_TYPES = [
        "PERSON",         # Individuals
        "ORGANIZATION",   # Companies, agencies, groups
        "LOCATION",       # Cities, countries, addresses
        "EVENT",          # Meetings, incidents, conferences
        "DATE",           # Specific dates or ranges
        "DOCUMENT",       # Referenced documents
        "PHONE",          # Phone numbers
        "EMAIL",          # Email addresses
        "MONEY",          # Financial amounts
        "LEGAL",          # Case numbers, statutes
    ]

    # Relationship types
    RELATIONSHIP_TYPES = [
        "works_at",
        "employed_by",
        "located_in",
        "based_in",
        "attended",
        "participated_in",
        "mentioned_in",
        "associated_with",
        "owns",
        "controls",
        "transacted_with",
        "communicated_with",
    ]

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "claude-opus-4-5-20251101",
                 confidence_threshold: float = 0.7,
                 output_dir: str = "data/processed"):
        """
        Initialize entity extractor

        Args:
            api_key: Anthropic API key (or from ANTHROPIC_API_KEY env var)
            model: Claude model to use
            confidence_threshold: Minimum confidence to keep entities (0-1)
            output_dir: Where to save extracted data
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set ANTHROPIC_API_KEY env var or pass api_key parameter")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.output_dir = Path(output_dir)

    def extract_from_chunk(self, chunk_text: str, chunk_id: str, document_id: str,
                          page_number: Optional[int] = None) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract entities and relationships from a single document chunk

        Args:
            chunk_text: Text to analyze
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            page_number: Optional page number

        Returns:
            Tuple of (entities list, relationships list)
        """
        # Build extraction prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(chunk_text, document_id, page_number)

        # Call Claude API with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,  # Increased for large documents with many entities
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )

                # Extract JSON from response
                response_text = response.content[0].text
                extraction_data = self._parse_extraction_response(response_text)

                # Convert to Entity and Relationship objects
                entities = self._build_entities(
                    extraction_data.get("entities", []),
                    chunk_id=chunk_id,
                    document_id=document_id,
                    page_number=page_number
                )

                relationships = self._build_relationships(
                    extraction_data.get("relationships", []),
                    chunk_id=chunk_id,
                    document_id=document_id,
                    page_number=page_number
                )

                # Filter by confidence
                entities = [e for e in entities if e.confidence >= self.confidence_threshold]
                relationships = [r for r in relationships if r.confidence >= self.confidence_threshold]

                return entities, relationships

            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

            except Exception as e:
                print(f"Error extracting from chunk {chunk_id}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return [], []  # Return empty on final failure

        return [], []

    def extract_from_document(self, chunks: List, document_metadata: Dict) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract entities and relationships from all chunks of a document

        Args:
            chunks: List of DocumentChunk objects
            document_metadata: Document metadata dict

        Returns:
            Tuple of (all entities, all relationships)
        """
        all_entities = []
        all_relationships = []

        print(f"\nExtracting entities from {len(chunks)} chunks...")

        for i, chunk in enumerate(chunks):
            print(f"  Processing chunk {i+1}/{len(chunks)}...", end="\r")

            entities, relationships = self.extract_from_chunk(
                chunk_text=chunk.text,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                page_number=chunk.page_number
            )

            all_entities.extend(entities)
            all_relationships.extend(relationships)

            # Small delay to avoid rate limits
            time.sleep(0.5)

        print(f"\n✓ Extracted {len(all_entities)} entities and {len(all_relationships)} relationships")

        # Deduplicate entities within document
        all_entities = self._deduplicate_entities(all_entities)

        # Save results
        self._save_extraction_results(document_metadata['document_id'], all_entities, all_relationships)

        return all_entities, all_relationships

    def _build_system_prompt(self) -> str:
        """Build the system prompt for entity extraction"""
        return f"""You are an expert document analyst specializing in intelligence analysis and entity extraction.

Your task is to extract ALL named entities and their relationships from provided text with high accuracy.

**Entity Types to Extract:**
{', '.join(self.ENTITY_TYPES)}

**For each entity, provide:**
- Unique ID (e.g., "e_001")
- Type (from list above)
- Text (exactly as it appears in document)
- Confidence score (0.0-1.0, where 1.0 is certain)

**Relationship Types:**
{', '.join(self.RELATIONSHIP_TYPES)}

**For each relationship:**
- Unique ID (e.g., "r_001")
- Source entity ID
- Target entity ID
- Relationship type (from list above)
- Confidence score (0.0-1.0)
- Evidence (exact quote from text supporting this relationship)

**Critical Rules:**
1. Extract ALL entities mentioned, even if uncertain (but reflect in confidence score)
2. Only create relationships you can support with evidence from the text
3. Use precise confidence scores (don't default to 0.9 for everything)
4. Preserve exact text as it appears (including capitalization, titles, abbreviations)
5. For PERSON entities, include full names with titles if present
6. For LOCATION entities, include full addresses when available
7. For DATE entities, preserve exact format from text

**Output Format:**
Return ONLY valid JSON with this exact structure (no markdown, no explanations):

{{
  "entities": [
    {{
      "id": "e_001",
      "type": "PERSON",
      "text": "John Smith",
      "confidence": 0.95
    }}
  ],
  "relationships": [
    {{
      "id": "r_001",
      "source_id": "e_001",
      "target_id": "e_002",
      "relationship_type": "works_at",
      "confidence": 0.88,
      "evidence": "John Smith is CEO of ACME Corporation"
    }}
  ]
}}

Be thorough. Extract everything. This data is used for intelligence analysis."""

    def _build_user_prompt(self, chunk_text: str, document_id: str, page_number: Optional[int] = None) -> str:
        """Build the user prompt with document context"""
        page_info = f"Page {page_number}" if page_number else "Unknown page"
        return f"""Document ID: {document_id}
{page_info}

Text to analyze:

---
{chunk_text}
---

Extract all entities and relationships from the above text in JSON format:"""

    def _parse_extraction_response(self, response_text: str) -> Dict:
        """Parse Claude's response and extract JSON"""
        # Claude sometimes wraps JSON in markdown code blocks
        if "```json" in response_text:
            # Extract JSON from code block
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        else:
            json_str = response_text.strip()

        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response was: {response_text[:200]}...")
            return {"entities": [], "relationships": []}

    def _build_entities(self, entities_data: List[Dict], chunk_id: str,
                       document_id: str, page_number: Optional[int]) -> List[Entity]:
        """Convert raw entity dicts to Entity objects"""
        entities = []
        for i, entity_dict in enumerate(entities_data):
            entity = Entity(
                id=f"{document_id}_{entity_dict.get('id', f'e_{i:04d}')}",
                type=entity_dict.get('type', 'UNKNOWN'),
                text=entity_dict.get('text', ''),
                confidence=entity_dict.get('confidence', 0.5),
                source_document=document_id,
                source_chunk=chunk_id,
                page_number=page_number,
                metadata=entity_dict.get('metadata', {})
            )
            entities.append(entity)
        return entities

    def _build_relationships(self, rels_data: List[Dict], chunk_id: str,
                            document_id: str, page_number: Optional[int]) -> List[Relationship]:
        """Convert raw relationship dicts to Relationship objects"""
        relationships = []
        for i, rel_dict in enumerate(rels_data):
            relationship = Relationship(
                id=f"{document_id}_{rel_dict.get('id', f'r_{i:04d}')}",
                source_id=f"{document_id}_{rel_dict.get('source_id', '')}",
                target_id=f"{document_id}_{rel_dict.get('target_id', '')}",
                relationship_type=rel_dict.get('relationship_type', 'associated_with'),
                confidence=rel_dict.get('confidence', 0.5),
                evidence=rel_dict.get('evidence', ''),
                source_document=document_id,
                source_chunk=chunk_id,
                page_number=page_number,
                metadata=rel_dict.get('metadata', {})
            )
            relationships.append(relationship)
        return relationships

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities (same text and type)"""
        seen = {}
        unique_entities = []

        for entity in entities:
            key = (entity.text.lower(), entity.type)
            if key not in seen:
                seen[key] = entity
                unique_entities.append(entity)
            else:
                # Keep entity with higher confidence
                if entity.confidence > seen[key].confidence:
                    unique_entities.remove(seen[key])
                    seen[key] = entity
                    unique_entities.append(entity)

        return unique_entities

    def _save_extraction_results(self, document_id: str, entities: List[Entity], relationships: List[Relationship]):
        """Save extracted entities and relationships to JSON"""
        doc_dir = self.output_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        # Save entities
        entities_data = [entity.to_dict() for entity in entities]
        with open(doc_dir / "entities.json", 'w', encoding='utf-8') as f:
            json.dump(entities_data, f, indent=2, ensure_ascii=False)

        # Save relationships
        relationships_data = [rel.to_dict() for rel in relationships]
        with open(doc_dir / "relationships.json", 'w', encoding='utf-8') as f:
            json.dump(relationships_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Saved extraction results to {doc_dir}")


# Example usage
if __name__ == "__main__":
    # Example: Extract from a test chunk
    extractor = EntityExtractor()

    test_chunk = """
    John Smith, CEO of ACME Corporation, met with Jane Doe from TechStart Inc
    at the Hilton Hotel in New York on January 15, 2024. They discussed a
    potential merger worth $500 million.
    """

    entities, relationships = extractor.extract_from_chunk(
        chunk_text=test_chunk,
        chunk_id="test_chunk_001",
        document_id="test_doc",
        page_number=1
    )

    print(f"\nExtracted {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.type}: {entity.text} (confidence: {entity.confidence:.2f})")

    print(f"\nExtracted {len(relationships)} relationships:")
    for rel in relationships:
        print(f"  - {rel.relationship_type}: {rel.evidence[:50]}...")
