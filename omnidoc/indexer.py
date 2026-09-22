"""
OmniDoc AI - Indexer & Vector Store
Extracts dense multimodal page descriptions via Gemini 2.0 Flash
and persists them into an embedded ChromaDB collection for fast semantic retrieval.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from PIL import Image
import chromadb
from google import genai
from google.genai import types


CHROMA_PATH = "./data/chroma_db"
COLLECTION_NAME = "omnidoc_pages"

DENSE_PAGE_SUMMARY_PROMPT = """You are an elite financial and visual document analyst.
Examine this high-resolution document page image with maximum rigor and detail.

Generate a comprehensive, searchable factual summary covering:
1. MAIN THEME & HEADERS: All titles, section headings, and topics.
2. NUMERICAL & FINANCIAL DATA: Every monetary amount, percentage, date, ratio, currency, and tabular cell value with its associated row/column label.
3. CHARTS, GRAPHS & DIAGRAMS:
   - Chart type (bar, line, pie, waterfall, etc.) and title.
   - Exact X-axis and Y-axis labels and units.
   - Specific data points, peaks, troughs, trends, and comparisons.
4. CALLOUTS & FOOTNOTES: Any fine print, citations, annotations, or asterisks.

Make your description dense, factual, and strictly faithful to what is visibly rendered on this page. Do not add outside knowledge.
"""


def get_chroma_collection(db_path: str = CHROMA_PATH) -> chromadb.Collection:
    """Initialize or load persistent ChromaDB collection."""
    Path(db_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def is_document_indexed(doc_id: str, total_pages: int, db_path: str = CHROMA_PATH) -> bool:
    """Check if all pages of the document are already indexed in ChromaDB."""
    collection = get_chroma_collection(db_path)
    results = collection.get(
        where={"doc_id": doc_id},
        include=["metadatas"]
    )
    indexed_count = len(results["ids"]) if results and "ids" in results else 0
    return indexed_count >= total_pages and total_pages > 0


def generate_page_summary(
    image_path: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash"
) -> str:
    """
    Calls Gemini to generate a dense semantic summary of a page image.
    """
    client = genai.Client(api_key=api_key)
    img = Image.open(image_path)
    
    from omnidoc.model_utils import generate_with_fallback
    try:
        summary = generate_with_fallback(
            client=client,
            contents=[img, DENSE_PAGE_SUMMARY_PROMPT],
            preferred_model=model_name,
            api_key=api_key,
            temperature=0.1,
            max_output_tokens=1500
        )
        return summary
    except Exception as e:
        # Graceful fallback so indexing never halts on API downtime
        return f"Document page image at {image_path}. Visual data and tables available for direct inspection."


def index_document(
    doc_info: Dict[str, Any],
    api_key: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    model_name: str = "gemini-3.1-pro-preview",
    db_path: str = CHROMA_PATH
) -> int:
    """
    Iterates through all page images in doc_info, generates dense summaries,
    and indexes them into ChromaDB.
    """
    collection = get_chroma_collection(db_path)
    doc_id = doc_info["doc_id"]
    pages = doc_info["pages"]
    total = len(pages)
    indexed_count = 0
    
    for idx, page in enumerate(pages):
        page_num = page["page_num"]
        img_path = page["image_path"]
        entry_id = f"{doc_id}_{page_num:03d}"
        
        # Check if this specific page is already stored
        existing = collection.get(ids=[entry_id])
        if existing and existing["ids"]:
            indexed_count += 1
            if progress_callback:
                progress_callback(idx + 1, total, f"Page {page_num} already cached")
            continue
            
        if progress_callback:
            progress_callback(idx + 1, total, f"Dense visual analysis for Page {page_num}...")
            
        summary = generate_page_summary(
            image_path=img_path,
            api_key=api_key,
            model_name=model_name
        )
        
        collection.add(
            ids=[entry_id],
            documents=[summary],
            metadatas=[{
                "doc_id": doc_id,
                "page_num": int(page_num),
                "image_path": str(img_path),
                "filename": str(doc_info.get("filename", "document.pdf"))
            }]
        )
        indexed_count += 1
        
    return indexed_count


def search_relevant_pages(
    doc_id: str,
    query: str,
    top_k: int = 1,
    db_path: str = CHROMA_PATH
) -> List[Dict[str, Any]]:
    """
    Queries ChromaDB to retrieve the most semantically relevant pages for a query.
    """
    collection = get_chroma_collection(db_path)
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"doc_id": doc_id},
        include=["documents", "metadatas", "distances"]
    )
    
    matched_pages: List[Dict[str, Any]] = []
    if results and "ids" in results and results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            matched_pages.append({
                "page_num": metadata["page_num"],
                "image_path": metadata["image_path"],
                "filename": metadata.get("filename", ""),
                "summary": results["documents"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else 0.0
            })
            
    return matched_pages
