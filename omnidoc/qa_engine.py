"""
OmniDoc AI - Multimodal QA Engine
Passes high-resolution page images and user queries directly to Gemini 2.5 Pro
with temperature=0.0 and strict Zero-Hallucination Guardrails.
Now includes bounding box evidence regions for visual source attribution.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
from google import genai
from google.genai import types
from omnidoc.indexer import search_relevant_pages
from omnidoc.bbox_overlay import parse_bbox_from_response, draw_bounding_boxes


STRICT_MULTIMODAL_PROMPT = """You are OmniDoc AI, a zero-tolerance document intelligence and compliance auditor operating in regulated industries (Financial Auditing, Medical Records, Legal Compliance).

You have been provided with:
1. An authentic high-resolution image of a specific page from the source document.
2. The user's query: "{query}"

MANDATORY COMPLIANCE RULES:
1. GROUND TRUTH RESTRICTION: You must answer SOLELY based on information visually and unambiguously present in this page image (text, tables, bar/line/pie charts, axes, labels, footnotes).
2. NO SPECULATION: Never assume, extrapolate, or estimate figures not explicitly visible or computable directly from the image.
3. ZERO-HALLUCINATION GUARDRAIL:
   - If the metric, date, table row, chart value, or question cannot be conclusively verified and read from this page image, you MUST set the answer to:
     [DATA_MISSING] followed by a concise explanation of what information is absent.
   - Do NOT try to be helpful by guessing or using general knowledge.
4. VISUAL ATTRIBUTION:
   - When answering, explicitly cite the visual anchor (e.g., "According to the bar chart titled 'Q3 EBITDA'...", "In the table row labeled 'Operating Expenses'...").
   - Quote exact figures with their units and currencies ($M, %, bps, etc.).
5. MULTILINGUAL FIDELITY:
   - Detect the language/dialect of the user's question (e.g., English, Tamil, Hindi, Tanglish).
   - Respond in that exact same language, while keeping financial numbers, company names, and units accurate.

VISUAL ELEMENT INVENTORY (MANDATORY):
Before answering, you MUST scan the entire page image and identify EVERY visual element present:
- Every table, chart (bar, line, pie, waterfall, etc.), graph, diagram, text block, callout, and footnote.
- For each element, determine whether it is RELEVANT to the user's query or NOT.
- In your response, you MUST report:
  a) Which elements you USED to derive your answer (with bounding boxes).
  b) Which elements you DID NOT USE, listing each one by name/description and why it was not relevant.
  c) The total count of visual elements found vs. how many were used.

CRITICAL OUTPUT FORMAT:
You MUST respond with a valid JSON object (no extra text before or after) in this exact structure:

```json
{{
    "answer": "Your detailed answer text here, citing visual anchors and exact figures...",
    "evidence_regions": [
        {{
            "label": "Short label for the region used (e.g., 'Q4 Revenue Bar', 'Profit Table Row')",
            "y_min": <top coordinate 0-1000>,
            "x_min": <left coordinate 0-1000>,
            "y_max": <bottom coordinate 0-1000>,
            "x_max": <right coordinate 0-1000>
        }}
    ],
    "visual_inventory": {{
        "total_elements": <total number of visual elements found on the page>,
        "used_count": <number of elements used to answer the query>,
        "skipped_count": <number of elements NOT used>,
        "skipped_elements": [
            {{
                "name": "Name/title of the skipped element (e.g., 'Bar Chart: Quarterly Revenue')",
                "reason": "Brief reason it was not used (e.g., 'Not relevant to the query about profit margins')"
            }}
        ]
    }}
}}
```

COORDINATE SYSTEM:
- The image is normalized to a 1000x1000 grid.
- (0, 0) is the top-left corner, (1000, 1000) is the bottom-right corner.
- y_min/y_max are vertical (top/bottom), x_min/x_max are horizontal (left/right).
- Draw bounding boxes TIGHTLY around the specific chart, table, graph bar, row, or text region you used to derive your answer.
- Include ALL regions you referenced. If you read from a table AND a bar chart, include bounding boxes for BOTH.
- If [DATA_MISSING], set evidence_regions to an empty array [].

Now analyze the image with surgical precision and provide your JSON response:
"""


def answer_document_query(
    doc_id: str,
    query: str,
    api_key: str,
    model_name: str = "gemini-3.1-pro-preview",
    target_page: Optional[int] = None,
    doc_pages: Optional[list] = None
) -> Dict[str, Any]:
    """
    Executes Multimodal RAG:
    1. Retrieves most relevant page from ChromaDB (or uses target_page if specified).
    2. Passes raw high-res page image + query to Gemini VLM.
    3. Parses structured JSON response with bounding boxes.
    4. Draws visual boundary overlays on the source page image.
    5. Evaluates Zero-Hallucination guardrail [DATA_MISSING].
    """
    client = genai.Client(api_key=api_key)
    
    # Step 1: Retrieval
    matched_page = None
    if target_page is not None and doc_pages:
        for p in doc_pages:
            if p["page_num"] == target_page:
                matched_page = {
                    "page_num": p["page_num"],
                    "image_path": p["image_path"],
                    "summary": "Manual page selection"
                }
                break
                
    if not matched_page:
        relevant_pages = search_relevant_pages(doc_id=doc_id, query=query, top_k=1)
        if relevant_pages:
            matched_page = relevant_pages[0]
        elif doc_pages and len(doc_pages) > 0:
            # Graceful fallback: If vector store hasn't finished indexing or document is 1 page,
            # use the active page or first page rather than failing with [DATA_MISSING]
            fallback_page = doc_pages[0]
            if target_page:
                for p in doc_pages:
                    if p["page_num"] == target_page:
                        fallback_page = p
                        break
            matched_page = {
                "page_num": fallback_page["page_num"],
                "image_path": fallback_page["image_path"],
                "summary": "Direct page analysis"
            }
        else:
            return {
                "answer": "[DATA_MISSING] No matching page could be retrieved from the document.",
                "is_data_missing": True,
                "missing_reason": "No matching page found in the vector index for this document.",
                "source_page": None,
                "source_image_path": None,
                "annotated_image_path": None,
                "bounding_boxes": [],
                "visual_inventory": {"total_elements": 0, "used_count": 0, "skipped_count": 0, "skipped_elements": []},
            }

    image_path = matched_page["image_path"]
    page_num = matched_page["page_num"]
    
    if not Path(image_path).exists():
        return {
            "answer": "[DATA_MISSING] Source page image file is unavailable on disk.",
            "is_data_missing": True,
            "missing_reason": f"Page image at {image_path} could not be loaded.",
            "source_page": page_num,
            "source_image_path": None,
            "annotated_image_path": None,
            "bounding_boxes": [],
            "visual_inventory": {"total_elements": 0, "used_count": 0, "skipped_count": 0, "skipped_elements": []},
        }
        
    # Step 2: Multimodal Reasoning with Gemini VLM
    pil_image = Image.open(image_path)
    prompt = STRICT_MULTIMODAL_PROMPT.format(query=query)
    
    from omnidoc.model_utils import generate_with_fallback
    raw_response = generate_with_fallback(
        client=client,
        contents=[pil_image, prompt],
        preferred_model=model_name,
        api_key=api_key,
        temperature=0.0,
        max_output_tokens=2500
    )
    
    # Step 3: Parse structured response (answer + bounding boxes + visual inventory)
    answer_text, bounding_boxes, visual_inventory = parse_bbox_from_response(raw_response)
    
    # Step 4: Draw bounding box overlays on the source page image
    annotated_image_path = None
    if bounding_boxes:
        try:
            _, annotated_image_path = draw_bounding_boxes(
                image_path=image_path,
                bounding_boxes=bounding_boxes,
                save=True
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Bounding box overlay failed: {e}")
    
    # Step 5: Evaluate Guardrail
    is_missing = "[DATA_MISSING]" in answer_text
    missing_reason = ""
    
    if is_missing:
        # Extract explanation following the flag
        parts = answer_text.split("[DATA_MISSING]")
        missing_reason = parts[1].strip() if len(parts) > 1 else "The requested information is not visually verifiable in the source document."

    return {
        "answer": answer_text,
        "is_data_missing": is_missing,
        "missing_reason": missing_reason,
        "source_page": page_num,
        "source_image_path": image_path,
        "annotated_image_path": annotated_image_path,
        "bounding_boxes": bounding_boxes,
        "visual_inventory": visual_inventory,
        "summary": matched_page.get("summary", "")
    }

