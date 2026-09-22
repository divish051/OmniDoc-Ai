"""
OmniDoc AI - PDF Processor
Slices PDF pages into high-resolution PNG images using PyMuPDF (fitz)
for spatial preservation of charts, tables, and visual layout.
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, List, Any
import pymupdf


def compute_file_hash(data: bytes) -> str:
    """Compute SHA-256 hash of raw file bytes for caching."""
    return hashlib.sha256(data).hexdigest()[:16]


def extract_pdf_pages_as_images(
    file_bytes: bytes,
    filename: str,
    output_dir: str = "./data/documents",
    dpi_scale: float = 2.0
) -> Dict[str, Any]:
    """
    Converts each page of a PDF into a high-resolution PNG image.
    
    Args:
        file_bytes: Raw bytes of the PDF file.
        filename: Original file name.
        output_dir: Directory where sliced PNGs will be stored.
        dpi_scale: Zoom matrix multiplier (2.0 = ~144-200 DPI high resolution).
        
    Returns:
        Dictionary containing doc_id, filename, total_pages, and page details.
    """
    doc_id = compute_file_hash(file_bytes)
    doc_dir = Path(output_dir) / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    pages_data: List[Dict[str, Any]] = []
    
    matrix = pymupdf.Matrix(dpi_scale, dpi_scale)
    
    for idx, page in enumerate(doc):
        page_num = idx + 1
        img_filename = f"page_{page_num:03d}.png"
        img_path = doc_dir / img_filename
        
        # Only render if not already cached on disk
        if not img_path.exists():
            pix = page.get_pixmap(matrix=matrix)
            pix.save(str(img_path))
            
        pages_data.append({
            "page_num": page_num,
            "image_path": str(img_path.resolve()),
            "width": page.rect.width,
            "height": page.rect.height,
        })
        
    doc.close()
    
    return {
        "doc_id": doc_id,
        "filename": filename,
        "total_pages": total_pages,
        "pages": pages_data,
        "doc_dir": str(doc_dir.resolve())
    }
