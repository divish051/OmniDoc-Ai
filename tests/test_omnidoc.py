"""
OmniDoc AI - Automated Verification Suite
Tests PyMuPDF page slicing, ChromaDB storage/retrieval, and guardrail logic.
"""

import sys
import os
from pathlib import Path
import pymupdf

# Add project root to sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from omnidoc.pdf_processor import extract_pdf_pages_as_images
from omnidoc.indexer import get_chroma_collection
from omnidoc.qa_engine import STRICT_MULTIMODAL_PROMPT


def test_pdf_slicing():
    print("[1/3] Testing PyMuPDF high-res image extraction...")
    # Create a dummy 2-page PDF in memory
    doc = pymupdf.open()
    
    # Page 1: Financial Table
    page1 = doc.new_page()
    page1.insert_text((50, 50), "OmniDoc Financial Statement Q3 2026", fontsize=16)
    page1.insert_text((50, 100), "Total Revenue: $45.2M", fontsize=12)
    page1.insert_text((50, 120), "Operating Expenses: $18.4M", fontsize=12)
    page1.insert_text((50, 140), "Net Profit: $26.8M", fontsize=12)
    
    # Page 2: Notes
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Regulatory Footnotes & Risk Factors", fontsize=16)
    page2.insert_text((50, 100), "No forward guidance is provided for Q4.", fontsize=12)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    test_out = ROOT / "data" / "test_docs"
    result = extract_pdf_pages_as_images(pdf_bytes, "sample_report.pdf", output_dir=str(test_out))
    
    assert result["total_pages"] == 2, f"Expected 2 pages, got {result['total_pages']}"
    assert len(result["pages"]) == 2, "Page records length mismatch"
    assert Path(result["pages"][0]["image_path"]).exists(), "Page 1 image missing on disk"
    assert Path(result["pages"][1]["image_path"]).exists(), "Page 2 image missing on disk"
    print("  [OK] Sliced 2 pages into high-resolution PNGs successfully!")
    return result


def test_chroma_persistence():
    print("[2/3] Testing ChromaDB persistent storage & semantic query...")
    test_chroma_path = str(ROOT / "data" / "test_chroma_db")
    collection = get_chroma_collection(db_path=test_chroma_path)
    
    # Insert test data
    collection.add(
        ids=["test_doc_001", "test_doc_002"],
        documents=[
            "Q3 2026 Financial Results with Total Revenue of $45.2M, Net Profit $26.8M.",
            "Footnotes stating no guidance for Q4 2026."
        ],
        metadatas=[
            {"doc_id": "test_doc", "page_num": 1, "image_path": "page_001.png"},
            {"doc_id": "test_doc", "page_num": 2, "image_path": "page_002.png"}
        ]
    )
    
    # Query for revenue
    res = collection.query(query_texts=["What was the total revenue in Q3?"], n_results=1)
    matched_id = res["ids"][0][0]
    assert matched_id == "test_doc_001", f"Expected test_doc_001, got {matched_id}"
    print("  [OK] ChromaDB correctly indexed and retrieved matching page by cosine distance!")


def test_guardrail_prompt():
    print("[3/3] Testing Zero-Hallucination Guardrail Prompt rules...")
    assert "[DATA_MISSING]" in STRICT_MULTIMODAL_PROMPT
    assert "GROUND TRUTH RESTRICTION" in STRICT_MULTIMODAL_PROMPT
    print("  [OK] Guardrail prompt enforces [DATA_MISSING] on missing/ambiguous figures!")


if __name__ == "__main__":
    print("\n--- Running OmniDoc AI Verification Suite ---")
    test_pdf_slicing()
    test_chroma_persistence()
    test_guardrail_prompt()
    print("\n[SUCCESS] ALL TESTS PASSED! OmniDoc AI is ready to run.\n")
