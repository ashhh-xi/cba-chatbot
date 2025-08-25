#!/usr/bin/env python3
"""
Preprocess CBA documents and create embeddings for RAG chatbot.
- Loads PDFs and HTML text files
- Splits into chunks
- Creates embeddings using sentence-transformers
- Stores in FAISS vector database

Run:
  python scripts/embed.py
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("backend/data/cba_pdfs")
SITE_TEXT_DIR = Path("backend/data/site_text")
INDEX_DIR = Path("backend/index")

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


class CustomTextLoader:
    """Loader for crawled HTML text files"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
    
    def load(self) -> List[Document]:
        with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        # Extract URL from first line if present
        lines = content.split('\n')
        url = lines[0] if lines and lines[0].startswith('http') else str(self.file_path.name)
        text = '\n'.join(lines[1:]) if lines and lines[0].startswith('http') else content
        
        return [Document(
            page_content=text,
            metadata={
                "source": str(self.file_path.name),
                "url": url,
                "type": "webpage"
            }
        )]


def load_documents() -> List[Document]:
    """Load all documents from PDF and text directories"""
    documents = []
    
    # Load PDFs
    logger.info("Loading PDF documents...")
    for pdf_path in DATA_DIR.glob("**/*.pdf"):
        try:
            loader = PyPDFLoader(str(pdf_path))
            pdf_docs = loader.load()
            for doc in pdf_docs:
                doc.metadata.update({
                    "source": str(pdf_path.name),
                    "type": "pdf",
                    "page": doc.metadata.get("page", 0)
                })
            documents.extend(pdf_docs)
            logger.info(f"Loaded PDF: {pdf_path.name} ({len(pdf_docs)} pages)")
        except Exception as e:
            logger.warning(f"Failed to load PDF {pdf_path.name}: {e}")
    
    # Load text files
    logger.info("Loading text documents...")
    for txt_path in SITE_TEXT_DIR.glob("**/*.txt"):
        try:
            loader = CustomTextLoader(txt_path)
            txt_docs = loader.load()
            documents.extend(txt_docs)
            logger.info(f"Loaded text: {txt_path.name}")
        except Exception as e:
            logger.warning(f"Failed to load text {txt_path.name}: {e}")
    
    logger.info(f"Total documents loaded: {len(documents)}")
    return documents


def chunk_documents(documents: List[Document]) -> List[Document]:
    """Split documents into chunks"""
    logger.info("Chunking documents...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
    
    return chunks


def create_embeddings():
    """Create embeddings and store in FAISS"""
    logger.info("Starting document preprocessing...")
    
    # Ensure directories exist
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load documents
    documents = load_documents()
    if not documents:
        logger.error("No documents found to process!")
        return
    
    # Create chunks
    chunks = chunk_documents(documents)
    
    # Create embeddings
    logger.info(f"Creating embeddings using {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    # Create vector store
    logger.info("Building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Save index
    vectorstore.save_local(str(INDEX_DIR))
    logger.info(f"FAISS index saved to {INDEX_DIR}")
    
    # Test retrieval
    logger.info("Testing retrieval...")
    test_query = "What are the fees for CBA credit cards?"
    results = vectorstore.similarity_search(test_query, k=3)
    logger.info(f"Test query: '{test_query}'")
    for i, doc in enumerate(results):
        logger.info(f"Result {i+1}: {doc.metadata['source']} - {doc.page_content[:100]}...")
    
    logger.info("✅ Document preprocessing complete!")


if __name__ == "__main__":
    create_embeddings()
