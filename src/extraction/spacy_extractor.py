"""
spaCy Entity Extractor - 100% FREE Local Entity Extraction

Uses spaCy for local, free entity extraction with no API costs.
No internet required, no API keys, completely open-source.
"""

import spacy
from spacy.tokens import Doc, Span
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from datetime import datetime
import re


@dataclass
class Entity:
    """Represents an extracted entity"""
    id: str
    type: str
    text: str
    confidence: float
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
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    evidence: str
    source_document: str
    source_chunk: str
    page_number: Optional[int] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items()}


class SpacyEntityExtractor:
    """
    FREE local entity extraction using spaCy

    No API costs, no internet required, 100% open-source

    Features:
    - Named Entity Recognition (PERSON, ORG, LOCATION, DATE, MONEY, etc.)
    - Relationship extraction using dependency parsing
    - Confidence scoring
    - Same interface as Claude extractor (drop-in replacement)
    """

    # Map spaCy entity types to our standard types
    ENTITY_TYPE_MAP = {
        'PERSON': 'PERSON',
        'ORG': 'ORGANIZATION',
        'GPE': 'LOCATION',        # Geopolitical entity (countries, cities)
        'LOC': 'LOCATION',        # Non-GPE locations
        'FAC': 'LOCATION',        # Facilities (buildings, airports)
        'DATE': 'DATE',
        'TIME': 'DATE',
        'MONEY': 'MONEY',
        'PERCENT': 'MONEY',
        'CARDINAL': 'NUMBER',
        'ORDINAL': 'NUMBER',
        'QUANTITY': 'NUMBER',
        'EVENT': 'EVENT',
        'WORK_OF_ART': 'DOCUMENT',
        'LAW': 'LEGAL',
        'LANGUAGE': 'OTHER',
        'NORP': 'ORGANIZATION',   # Nationalities or religious/political groups
        'PRODUCT': 'OTHER',
    }

    # Relationship patterns based on dependency parsing
    RELATIONSHIP_PATTERNS = {
        'works_at': ['nsubj', 'prep', 'pobj'],
        'employed_by': ['nsubjpass', 'agent', 'pobj'],
        'located_in': ['prep', 'pobj'],
        'based_in': ['prep', 'pobj'],
    }

    def __init__(self,
                 model: str = "en_core_web_sm",
                 confidence_threshold: float = 0.7,
                 output_dir: str = "data/processed"):
        """
        Initialize spaCy entity extractor

        Args:
            model: spaCy model to use (en_core_web_sm, en_core_web_md, en_core_web_lg)
            confidence_threshold: Minimum confidence to keep entities (0-1)
            output_dir: Where to save extracted data
        """
        self.confidence_threshold = confidence_threshold
        self.output_dir = Path(output_dir)

        # Load spaCy model
        try:
            self.nlp = spacy.load(model)
            print(f"✓ Loaded spaCy model: {model}")
        except OSError:
            print(f"✗ spaCy model '{model}' not found. Downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model])
            self.nlp = spacy.load(model)
            print(f"✓ Downloaded and loaded: {model}")

    def extract_from_chunk(self, chunk_text: str, chunk_id: str, document_id: str,
                          page_number: Optional[int] = None) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract entities and relationships from a text chunk using spaCy

        Args:
            chunk_text: Text to analyze
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            page_number: Optional page number

        Returns:
            Tuple of (entities list, relationships list)
        """
        # Process text with spaCy
        doc = self.nlp(chunk_text)

        # Extract entities
        entities = self._extract_entities(doc, chunk_id, document_id, page_number)

        # Extract relationships
        relationships = self._extract_relationships(doc, entities, chunk_id, document_id, page_number)

        # Filter by confidence
        entities = [e for e in entities if e.confidence >= self.confidence_threshold]
        relationships = [r for r in relationships if r.confidence >= self.confidence_threshold]

        return entities, relationships

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

        print(f"\n🔍 Extracting entities with spaCy (FREE, local processing)...")

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

        print(f"\n✓ Extracted {len(all_entities)} entities and {len(all_relationships)} relationships")

        # Deduplicate entities
        all_entities = self._deduplicate_entities(all_entities)

        # Save results
        self._save_extraction_results(document_metadata['document_id'], all_entities, all_relationships)

        return all_entities, all_relationships

    def _extract_entities(self, doc: Doc, chunk_id: str, document_id: str,
                         page_number: Optional[int]) -> List[Entity]:
        """Extract named entities from spaCy Doc"""
        entities = []
        entity_counter = 0

        for ent in doc.ents:
            # Map spaCy type to our standard type
            entity_type = self.ENTITY_TYPE_MAP.get(ent.label_, 'OTHER')

            # Skip if we don't recognize this type
            if entity_type == 'OTHER':
                continue

            # Calculate confidence (spaCy doesn't provide this, so we estimate)
            # Based on entity length, capitalization, and context
            confidence = self._estimate_confidence(ent, doc)

            entity = Entity(
                id=f"{document_id}_e_{entity_counter:04d}",
                type=entity_type,
                text=ent.text.strip(),
                confidence=confidence,
                source_document=document_id,
                source_chunk=chunk_id,
                page_number=page_number,
                metadata={
                    'spacy_label': ent.label_,
                    'start_char': ent.start_char,
                    'end_char': ent.end_char
                }
            )
            entities.append(entity)
            entity_counter += 1

        # Also extract emails and phone numbers with regex (spaCy sometimes misses these)
        email_entities = self._extract_emails(doc.text, chunk_id, document_id, page_number, entity_counter)
        entities.extend(email_entities)
        entity_counter += len(email_entities)

        phone_entities = self._extract_phones(doc.text, chunk_id, document_id, page_number, entity_counter)
        entities.extend(phone_entities)

        return entities

    def _extract_relationships(self, doc: Doc, entities: List[Entity],
                              chunk_id: str, document_id: str,
                              page_number: Optional[int]) -> List[Relationship]:
        """Extract relationships using dependency parsing"""
        relationships = []
        rel_counter = 0

        # Create entity lookup by text
        entity_lookup = {e.text.lower(): e for e in entities}

        # Method 1: Use dependency patterns to find relationships
        for token in doc:
            # Look for verb-based relationships (e.g., "John works at ACME")
            if token.pos_ == 'VERB':
                # Get subject and object
                subjects = [child for child in token.children if child.dep_ in ('nsubj', 'nsubjpass')]
                objects = [child for child in token.children if child.dep_ in ('dobj', 'pobj', 'attr')]

                for subj in subjects:
                    for obj in objects:
                        # Check if both are entities
                        subj_text = subj.text.lower()
                        obj_text = obj.text.lower()

                        source_entity = entity_lookup.get(subj_text)
                        target_entity = entity_lookup.get(obj_text)

                        if source_entity and target_entity:
                            # Determine relationship type based on verb
                            rel_type = self._classify_relationship(token.lemma_, source_entity.type, target_entity.type)

                            # Get evidence sentence
                            evidence = token.sent.text.strip()

                            relationship = Relationship(
                                id=f"{document_id}_r_{rel_counter:04d}",
                                source_id=source_entity.id,
                                target_id=target_entity.id,
                                relationship_type=rel_type,
                                confidence=0.75,  # Medium confidence for parsed relationships
                                evidence=evidence[:200],  # Limit evidence length
                                source_document=document_id,
                                source_chunk=chunk_id,
                                page_number=page_number
                            )
                            relationships.append(relationship)
                            rel_counter += 1

        # Method 2: Co-occurrence based relationships (entities mentioned near each other)
        relationships.extend(self._extract_cooccurrence_relationships(
            doc, entities, chunk_id, document_id, page_number, rel_counter
        ))

        return relationships

    def _extract_cooccurrence_relationships(self, doc: Doc, entities: List[Entity],
                                           chunk_id: str, document_id: str,
                                           page_number: Optional[int],
                                           start_counter: int) -> List[Relationship]:
        """Extract relationships based on entity co-occurrence in sentences"""
        relationships = []
        rel_counter = start_counter

        # Group entities by sentence
        for sent in doc.sents:
            sent_entities = []
            for ent in entities:
                if ent.metadata.get('start_char', -1) >= sent.start_char and \
                   ent.metadata.get('end_char', -1) <= sent.end_char:
                    sent_entities.append(ent)

            # Create 'mentioned_in' relationships for entities in same sentence
            if len(sent_entities) >= 2:
                for i, ent1 in enumerate(sent_entities):
                    for ent2 in sent_entities[i+1:]:
                        # Only create relationship if they're different types
                        if ent1.type != ent2.type:
                            relationship = Relationship(
                                id=f"{document_id}_r_{rel_counter:04d}",
                                source_id=ent1.id,
                                target_id=ent2.id,
                                relationship_type='associated_with',
                                confidence=0.6,  # Lower confidence for co-occurrence
                                evidence=sent.text.strip()[:200],
                                source_document=document_id,
                                source_chunk=chunk_id,
                                page_number=page_number
                            )
                            relationships.append(relationship)
                            rel_counter += 1

        return relationships

    def _classify_relationship(self, verb: str, source_type: str, target_type: str) -> str:
        """Classify relationship type based on verb and entity types"""
        # Map common verbs to relationship types
        verb_map = {
            'work': 'works_at' if target_type == 'ORGANIZATION' else 'associated_with',
            'employ': 'employed_by',
            'locate': 'located_in',
            'base': 'based_in',
            'own': 'owns',
            'control': 'controls',
            'meet': 'communicated_with',
            'contact': 'communicated_with',
            'call': 'communicated_with',
            'email': 'communicated_with',
            'attend': 'attended',
            'participate': 'participated_in',
        }

        return verb_map.get(verb, 'associated_with')

    def _estimate_confidence(self, ent: Span, doc: Doc) -> float:
        """Estimate confidence for an entity (spaCy doesn't provide this)"""
        confidence = 0.8  # Base confidence

        # Increase confidence for proper capitalization
        if ent.text[0].isupper():
            confidence += 0.05

        # Increase confidence for multi-word entities
        if len(ent.text.split()) > 1:
            confidence += 0.05

        # Increase confidence for entities in quotes
        context_start = max(0, ent.start_char - 10)
        context_end = min(len(doc.text), ent.end_char + 10)
        context = doc.text[context_start:context_end]
        if '"' in context or "'" in context:
            confidence += 0.05

        return min(confidence, 1.0)

    def _extract_emails(self, text: str, chunk_id: str, document_id: str,
                       page_number: Optional[int], start_counter: int) -> List[Entity]:
        """Extract email addresses using regex"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)

        entities = []
        for i, email in enumerate(emails):
            entity = Entity(
                id=f"{document_id}_e_{start_counter + i:04d}",
                type='EMAIL',
                text=email,
                confidence=0.95,  # High confidence for regex matches
                source_document=document_id,
                source_chunk=chunk_id,
                page_number=page_number,
                metadata={'extraction_method': 'regex'}
            )
            entities.append(entity)

        return entities

    def _extract_phones(self, text: str, chunk_id: str, document_id: str,
                       page_number: Optional[int], start_counter: int) -> List[Entity]:
        """Extract phone numbers using regex"""
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)

        entities = []
        for i, phone in enumerate(phones):
            entity = Entity(
                id=f"{document_id}_e_{start_counter + i:04d}",
                type='PHONE',
                text=phone,
                confidence=0.9,
                source_document=document_id,
                source_chunk=chunk_id,
                page_number=page_number,
                metadata={'extraction_method': 'regex'}
            )
            entities.append(entity)

        return entities

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

    def _save_extraction_results(self, document_id: str, entities: List[Entity],
                                 relationships: List[Relationship]):
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
    extractor = SpacyEntityExtractor()

    test_text = """
    John Smith, CEO of ACME Corporation, met with Jane Doe from TechStart Inc
    at the Hilton Hotel in New York on January 15, 2024. They discussed a
    potential merger worth $500 million. Contact: jsmith@acme.com, (555) 123-4567.
    """

    # Mock chunk for testing
    from dataclasses import dataclass

    @dataclass
    class MockChunk:
        text: str
        chunk_id: str
        document_id: str
        page_number: int = 1

    chunk = MockChunk(test_text, "test_001", "doc_test", 1)
    entities, relationships = extractor.extract_from_chunk(
        chunk.text, chunk.chunk_id, chunk.document_id, chunk.page_number
    )

    print(f"\n✓ Extracted {len(entities)} entities:")
    for ent in entities:
        print(f"  - [{ent.type}] {ent.text} (confidence: {ent.confidence:.2f})")

    print(f"\n✓ Extracted {len(relationships)} relationships:")
    for rel in relationships:
        print(f"  - {rel.relationship_type}")
