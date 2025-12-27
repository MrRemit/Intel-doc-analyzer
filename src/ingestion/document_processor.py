"""
Document Ingestion Module - PDF, DOCX, Email Processing

Handles extraction of text from various document formats with metadata preservation.
"""

import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
from datetime import datetime
import json


@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document"""
    chunk_id: str
    document_id: str
    text: str
    page_number: Optional[int] = None
    chunk_index: int = 0
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DocumentMetadata:
    """Metadata about the processed document"""
    document_id: str
    filename: str
    file_path: str
    file_type: str
    total_pages: int
    total_chars: int
    total_chunks: int
    processed_date: str
    file_hash: str
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "total_pages": self.total_pages,
            "total_chars": self.total_chars,
            "total_chunks": self.total_chunks,
            "processed_date": self.processed_date,
            "file_hash": self.file_hash,
            "metadata": self.metadata
        }


class DocumentProcessor:
    """
    Main document processing class

    Supports:
    - PDF files (text extraction, table detection)
    - DOCX files
    - Plain text files
    - Email files (EML, MBOX)

    Features:
    - Intelligent chunking (respects sentence boundaries)
    - Metadata preservation (page numbers, source)
    - Duplicate detection (file hashing)
    - Error handling and logging
    """

    def __init__(self,
                 max_chunk_size: int = 4000,
                 chunk_overlap: int = 200,
                 output_dir: str = "data/processed"):
        """
        Initialize document processor

        Args:
            max_chunk_size: Maximum characters per chunk (default: 4000 for Claude API)
            chunk_overlap: Character overlap between chunks (for context continuity)
            output_dir: Directory to store processed documents
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: str) -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """
        Process a document file (auto-detects format)

        Args:
            file_path: Path to document file

        Returns:
            Tuple of (chunks, metadata)

        Raises:
            ValueError: If file format not supported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type and route to appropriate handler
        suffix = path.suffix.lower()

        if suffix == '.pdf':
            return self.process_pdf(file_path)
        elif suffix == '.docx':
            return self.process_docx(file_path)
        elif suffix in ['.txt', '.md']:
            return self.process_text(file_path)
        elif suffix in ['.eml', '.msg']:
            return self.process_email(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def process_pdf(self, file_path: str, use_pdfplumber: bool = False) -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """
        Extract text from PDF file

        Args:
            file_path: Path to PDF file
            use_pdfplumber: If True, use pdfplumber (better for tables), else PyMuPDF (faster)

        Returns:
            Tuple of (chunks, metadata)
        """
        path = Path(file_path)
        document_id = self._generate_document_id(path)

        if use_pdfplumber:
            text_by_page = self._extract_with_pdfplumber(file_path)
        else:
            text_by_page = self._extract_with_pymupdf(file_path)

        # Create chunks from extracted text
        all_chunks = []
        chunk_counter = 0

        for page_num, page_text in enumerate(text_by_page, start=1):
            if not page_text.strip():
                continue

            # Split page into chunks if needed
            page_chunks = self._chunk_text(page_text)

            for chunk_text in page_chunks:
                chunk = DocumentChunk(
                    chunk_id=f"{document_id}_chunk_{chunk_counter:04d}",
                    document_id=document_id,
                    text=chunk_text,
                    page_number=page_num,
                    chunk_index=chunk_counter,
                    metadata={
                        "source_file": path.name,
                        "page": page_num
                    }
                )
                all_chunks.append(chunk)
                chunk_counter += 1

        # Calculate total characters
        total_chars = sum(len(chunk.text) for chunk in all_chunks)

        # Create metadata
        metadata = DocumentMetadata(
            document_id=document_id,
            filename=path.name,
            file_path=str(path.absolute()),
            file_type="pdf",
            total_pages=len(text_by_page),
            total_chars=total_chars,
            total_chunks=len(all_chunks),
            processed_date=datetime.now().isoformat(),
            file_hash=self._hash_file(file_path)
        )

        # Save to disk
        self._save_processed_document(document_id, all_chunks, metadata)

        return all_chunks, metadata

    def _extract_with_pymupdf(self, file_path: str) -> List[str]:
        """Extract text using PyMuPDF (fast, good for simple PDFs)"""
        doc = fitz.open(file_path)
        text_by_page = []

        for page in doc:
            text = page.get_text()
            text_by_page.append(text)

        doc.close()
        return text_by_page

    def _extract_with_pdfplumber(self, file_path: str) -> List[str]:
        """Extract text using pdfplumber (better for tables and complex layouts)"""
        text_by_page = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""

                # Also extract tables if present
                tables = page.extract_tables()
                if tables:
                    # Convert tables to text format
                    for table in tables:
                        table_text = "\n".join(["\t".join([str(cell) or "" for cell in row]) for row in table])
                        text += "\n\n[TABLE]\n" + table_text + "\n[/TABLE]\n"

                text_by_page.append(text)

        return text_by_page

    def process_docx(self, file_path: str) -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """Extract text from DOCX file"""
        from docx import Document

        path = Path(file_path)
        document_id = self._generate_document_id(path)

        doc = Document(file_path)

        # Extract all paragraphs
        full_text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])

        # Chunk the text
        chunks = self._chunk_text(full_text)

        all_chunks = []
        for idx, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                chunk_id=f"{document_id}_chunk_{idx:04d}",
                document_id=document_id,
                text=chunk_text,
                chunk_index=idx,
                metadata={
                    "source_file": path.name,
                }
            )
            all_chunks.append(chunk)

        metadata = DocumentMetadata(
            document_id=document_id,
            filename=path.name,
            file_path=str(path.absolute()),
            file_type="docx",
            total_pages=len(doc.sections),  # Approximate
            total_chars=len(full_text),
            total_chunks=len(all_chunks),
            processed_date=datetime.now().isoformat(),
            file_hash=self._hash_file(file_path)
        )

        self._save_processed_document(document_id, all_chunks, metadata)
        return all_chunks, metadata

    def process_text(self, file_path: str) -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """Process plain text file"""
        path = Path(file_path)
        document_id = self._generate_document_id(path)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            full_text = f.read()

        chunks = self._chunk_text(full_text)

        all_chunks = []
        for idx, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                chunk_id=f"{document_id}_chunk_{idx:04d}",
                document_id=document_id,
                text=chunk_text,
                chunk_index=idx,
                metadata={"source_file": path.name}
            )
            all_chunks.append(chunk)

        metadata = DocumentMetadata(
            document_id=document_id,
            filename=path.name,
            file_path=str(path.absolute()),
            file_type="text",
            total_pages=1,
            total_chars=len(full_text),
            total_chunks=len(all_chunks),
            processed_date=datetime.now().isoformat(),
            file_hash=self._hash_file(file_path)
        )

        self._save_processed_document(document_id, all_chunks, metadata)
        return all_chunks, metadata

    def process_email(self, file_path: str) -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """Extract text from email file (.eml)"""
        import email
        from email import policy

        path = Path(file_path)
        document_id = self._generate_document_id(path)

        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        # Extract email components
        subject = msg.get('Subject', '')
        sender = msg.get('From', '')
        recipient = msg.get('To', '')
        date = msg.get('Date', '')

        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

        # Construct full text with metadata
        full_text = f"""Subject: {subject}
From: {sender}
To: {recipient}
Date: {date}

{body}
"""

        chunks = self._chunk_text(full_text)

        all_chunks = []
        for idx, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                chunk_id=f"{document_id}_chunk_{idx:04d}",
                document_id=document_id,
                text=chunk_text,
                chunk_index=idx,
                metadata={
                    "source_file": path.name,
                    "subject": subject,
                    "from": sender,
                    "to": recipient,
                    "date": date
                }
            )
            all_chunks.append(chunk)

        metadata = DocumentMetadata(
            document_id=document_id,
            filename=path.name,
            file_path=str(path.absolute()),
            file_type="email",
            total_pages=1,
            total_chars=len(full_text),
            total_chunks=len(all_chunks),
            processed_date=datetime.now().isoformat(),
            file_hash=self._hash_file(file_path),
            metadata={
                "subject": subject,
                "from": sender,
                "to": recipient,
                "date": date
            }
        )

        self._save_processed_document(document_id, all_chunks, metadata)
        return all_chunks, metadata

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with smart boundary detection

        Tries to split on:
        1. Double newlines (paragraphs)
        2. Single newlines
        3. Periods (sentences)
        4. Character limit (as fallback)
        """
        if len(text) <= self.max_chunk_size:
            return [text]

        chunks = []
        current_chunk = ""

        # Split on paragraphs first
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            # If adding this paragraph exceeds limit, finalize current chunk
            if len(current_chunk) + len(para) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Add overlap from end of previous chunk
                    overlap = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                    current_chunk = overlap + para
                else:
                    # Paragraph itself is too long, split by sentences
                    sentences = para.split('. ')
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > self.max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                overlap = current_chunk[-self.chunk_overlap:]
                                current_chunk = overlap + sentence
                            else:
                                # Sentence too long, hard split
                                chunks.append(sentence[:self.max_chunk_size])
                                current_chunk = sentence[self.max_chunk_size:]
                        else:
                            current_chunk += sentence + '. '
            else:
                current_chunk += para + '\n\n'

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _generate_document_id(self, path: Path) -> str:
        """Generate unique document ID from filename and timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_hash = hashlib.md5(path.name.encode()).hexdigest()[:8]
        return f"doc_{name_hash}_{timestamp}"

    def _hash_file(self, file_path: str) -> str:
        """Generate SHA256 hash of file for duplicate detection"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _save_processed_document(self, document_id: str, chunks: List[DocumentChunk], metadata: DocumentMetadata):
        """Save processed chunks and metadata to disk"""
        doc_dir = self.output_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        # Save chunks
        chunks_data = [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "text": chunk.text,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata
            }
            for chunk in chunks
        ]

        with open(doc_dir / "chunks.json", 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)

        # Save metadata
        with open(doc_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"✓ Saved {len(chunks)} chunks to {doc_dir}")


# Example usage
if __name__ == "__main__":
    processor = DocumentProcessor()

    # Example: Process a PDF
    # chunks, metadata = processor.process_file("data/raw/document.pdf")
    # print(f"Processed: {metadata.filename}")
    # print(f"Total chunks: {metadata.total_chunks}")
    # print(f"First chunk preview: {chunks[0].text[:200]}...")

    print("Document Processor ready. Use processor.process_file(path) to extract text.")
