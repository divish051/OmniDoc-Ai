"""
OmniDoc AI - FastAPI REST API
Serves high-resolution page images, executes PyMuPDF PDF ingestion,
and powers multimodal Gemini 2.0 / 3.6 visual reasoning for the Next.js frontend.
"""

import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from omnidoc.pdf_processor import extract_pdf_pages_as_images
from omnidoc.indexer import is_document_indexed, index_document
from omnidoc.qa_engine import answer_document_query
from omnidoc.voice import transcribe_audio_bytes
from omnidoc.model_utils import get_available_gemini_models

app = FastAPI(
    title="OmniDoc AI API",
    description="Multimodal Document QA REST Backend for Next.js Frontend",
    version="1.0.0"
)

# Enable CORS for Next.js frontend on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCS_CACHE: dict = {}


class QueryRequest(BaseModel):
    doc_id: str
    query: str
    api_key: Optional[str] = None
    model_name: Optional[str] = "gemini-3.1-pro-preview"
    target_page: Optional[int] = None


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "OmniDoc AI Backend"}


@app.get("/api/models")
def list_models(api_key: Optional[str] = None):
    key = api_key or os.getenv("GEMINI_API_KEY") or ""
    models = get_available_gemini_models(key)
    return {"models": models}


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    contents = await file.read()
    doc_info = extract_pdf_pages_as_images(contents, file.filename)
    DOCS_CACHE[doc_info["doc_id"]] = doc_info
    
    # Trigger background/inline indexing if API key provided
    key = api_key or os.getenv("GEMINI_API_KEY") or ""
    if key and not is_document_indexed(doc_info["doc_id"], doc_info["total_pages"]):
        try:
            index_document(doc_info, api_key=key)
        except Exception:
            pass  # Resilient fallback to direct page inspection
            
    # Return formatted page metadata
    pages = [
        {
            "page_num": p["page_num"],
            "url": f"/api/page/{doc_info['doc_id']}/{p['page_num']}",
            "width": p["width"],
            "height": p["height"]
        }
        for p in doc_info["pages"]
    ]
    
    return {
        "doc_id": doc_info["doc_id"],
        "filename": doc_info["filename"],
        "total_pages": doc_info["total_pages"],
        "pages": pages
    }


@app.get("/api/page/{doc_id}/{page_num}")
def get_page_image(doc_id: str, page_num: int):
    doc_dir = Path("./data/documents") / doc_id
    img_path = doc_dir / f"page_{page_num:03d}.png"
    
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Page image not found")
        
    return FileResponse(img_path, media_type="image/png")


@app.post("/api/query")
def query_document(req: QueryRequest):
    key = req.api_key or os.getenv("GEMINI_API_KEY") or ""
    if not key:
        raise HTTPException(status_code=400, detail="Google Gemini API Key is required.")
        
    doc_info = DOCS_CACHE.get(req.doc_id)
    doc_pages = doc_info.get("pages") if doc_info else None
    
    result = answer_document_query(
        doc_id=req.doc_id,
        query=req.query,
        api_key=key,
        model_name=req.model_name or "gemini-2.5-pro",
        target_page=req.target_page,
        doc_pages=doc_pages
    )
    
    # Convert annotated image path to a URL
    annotated_path = result.get("annotated_image_path")
    if annotated_path:
        result["annotated_image_url"] = f"/api/annotated/{Path(annotated_path).name}"
    else:
        result["annotated_image_url"] = None
    
    return result


@app.get("/api/annotated/{filename}")
def get_annotated_image(filename: str):
    """Serve annotated page images with bounding box overlays."""
    img_path = Path("./data/annotated") / filename
    
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Annotated image not found")
        
    return FileResponse(img_path, media_type="image/png")


@app.post("/api/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    key = api_key or os.getenv("GEMINI_API_KEY") or ""
    if not key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required.")
        
    audio_bytes = await audio.read()
    text, err = transcribe_audio_bytes(audio_bytes, api_key=key, mime_type=audio.content_type or "audio/wav")
    
    if err:
        return {"error": err, "transcription": ""}
    return {"transcription": text, "error": None}

