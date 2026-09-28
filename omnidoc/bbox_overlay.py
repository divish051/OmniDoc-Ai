"""
OmniDoc AI - Bounding Box Overlay Engine
Draws visual boundary rectangles on document page images to show
exactly which region (chart, table, graph, text block) the AI
used to extract and verify its answer.
"""

import io
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


# Colors for multiple bounding boxes (RGBA)
BBOX_COLORS = [
    (0, 200, 255, 180),    # Cyan
    (255, 100, 100, 180),  # Red
    (100, 255, 100, 180),  # Green
    (255, 200, 50, 180),   # Gold
    (180, 100, 255, 180),  # Purple
    (255, 150, 50, 180),   # Orange
]

# Fill overlay (semi-transparent highlight)
BBOX_FILL_ALPHA = 35

ANNOTATED_DIR = "./data/annotated"


def normalize_bbox(bbox: Dict[str, Any], img_width: int, img_height: int) -> Tuple[int, int, int, int]:
    """
    Convert Gemini's normalized bounding box (0-1000 scale) to pixel coordinates.
    Gemini returns: [y_min, x_min, y_max, x_max] in 0-1000 scale.
    We accept dict with keys: y_min, x_min, y_max, x_max (all 0-1000).
    Returns: (left, top, right, bottom) in pixel coordinates.
    """
    x_min = bbox.get("x_min", 0)
    y_min = bbox.get("y_min", 0)
    x_max = bbox.get("x_max", 1000)
    y_max = bbox.get("y_max", 1000)

    left = int((x_min / 1000) * img_width)
    top = int((y_min / 1000) * img_height)
    right = int((x_max / 1000) * img_width)
    bottom = int((y_max / 1000) * img_height)

    # Clamp to image bounds
    left = max(0, min(left, img_width - 1))
    top = max(0, min(top, img_height - 1))
    right = max(left + 1, min(right, img_width))
    bottom = max(top + 1, min(bottom, img_height))

    return (left, top, right, bottom)


def draw_bounding_boxes(
    image_path: str,
    bounding_boxes: List[Dict[str, Any]],
    save: bool = True
) -> Tuple[Image.Image, Optional[str]]:
    """
    Draw colored bounding box rectangles on a document page image.
    
    Args:
        image_path: Path to the original page PNG image.
        bounding_boxes: List of dicts, each with:
            - label: str (e.g., "Q4 Revenue Bar", "Table Row 3")
            - y_min, x_min, y_max, x_max: int (0-1000 normalized coords)
        save: If True, saves the annotated image to disk and returns its path.
    
    Returns:
        (annotated_pil_image, saved_path_or_None)
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # Create a transparent overlay for filled rectangles
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Draw directly on original for outlines and labels
    draw = ImageDraw.Draw(img)

    # Try to load a reasonable font for labels
    font = None
    font_size = max(14, int(h * 0.018))
    try:
        # Try system fonts
        for font_path in [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
                break
    except Exception:
        pass
    if font is None:
        font = ImageFont.load_default()

    for idx, bbox in enumerate(bounding_boxes):
        color = BBOX_COLORS[idx % len(BBOX_COLORS)]
        r, g, b, a = color

        left, top, right, bottom = normalize_bbox(bbox, w, h)
        label = bbox.get("label", f"Region {idx + 1}")

        # 1. Draw semi-transparent fill
        fill_color = (r, g, b, BBOX_FILL_ALPHA)
        overlay_draw.rectangle([left, top, right, bottom], fill=fill_color)

        # 2. Draw thick border outline (3px)
        border_width = max(2, int(h * 0.004))
        for bw in range(border_width):
            draw.rectangle(
                [left - bw, top - bw, right + bw, bottom + bw],
                outline=(r, g, b, a)
            )

        # 3. Draw label tag at top-left corner
        label_text = f" {label} "
        text_bbox = font.getbbox(label_text)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        padding = 4

        # Label background
        label_bg_left = left
        label_bg_top = max(0, top - text_h - padding * 2)
        label_bg_right = left + text_w + padding * 2
        label_bg_bottom = top

        overlay_draw.rectangle(
            [label_bg_left, label_bg_top, label_bg_right, label_bg_bottom],
            fill=(r, g, b, 220)
        )

        # Label text (white on colored background)
        draw.text(
            (label_bg_left + padding, label_bg_top + padding // 2),
            label_text,
            fill=(255, 255, 255, 255),
            font=font
        )

    # Composite overlay onto original
    img = Image.alpha_composite(img, overlay)

    # Convert back to RGB for display/saving as PNG
    result = img.convert("RGB")

    saved_path = None
    if save:
        Path(ANNOTATED_DIR).mkdir(parents=True, exist_ok=True)
        # Create a unique filename based on original path + bbox content
        bbox_hash = hashlib.md5(str(bounding_boxes).encode()).hexdigest()[:8]
        orig_stem = Path(image_path).stem
        saved_path = str(Path(ANNOTATED_DIR) / f"{orig_stem}_bbox_{bbox_hash}.png")
        result.save(saved_path, "PNG")

    return result, saved_path


def parse_bbox_from_response(raw_response: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse Gemini's structured response to extract answer text, bounding boxes,
    and visual element inventory (used vs. skipped elements).
    
    Returns:
        (answer_text, list_of_bounding_boxes, visual_inventory_dict)
    """
    import json
    import re

    empty_inventory = {
        "total_elements": 0,
        "used_count": 0,
        "skipped_count": 0,
        "skipped_elements": []
    }

    # Try to find JSON block in the response
    json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*"answer"[\s\S]*\}', raw_response)
        if json_match:
            json_str = json_match.group(0)
        else:
            # No structured response found - return raw text with no boxes
            return raw_response.strip(), [], empty_inventory

    try:
        parsed = json.loads(json_str)
        answer = parsed.get("answer", raw_response)
        regions = parsed.get("evidence_regions", [])

        # Validate bounding box fields
        valid_regions = []
        for region in regions:
            if all(k in region for k in ["y_min", "x_min", "y_max", "x_max"]):
                # Ensure coordinates are within 0-1000 range
                region["y_min"] = max(0, min(1000, int(region["y_min"])))
                region["x_min"] = max(0, min(1000, int(region["x_min"])))
                region["y_max"] = max(0, min(1000, int(region["y_max"])))
                region["x_max"] = max(0, min(1000, int(region["x_max"])))
                if region["y_max"] > region["y_min"] and region["x_max"] > region["x_min"]:
                    valid_regions.append(region)

        # Extract visual inventory
        inventory = parsed.get("visual_inventory", empty_inventory)
        visual_inventory = {
            "total_elements": int(inventory.get("total_elements", 0)),
            "used_count": int(inventory.get("used_count", len(valid_regions))),
            "skipped_count": int(inventory.get("skipped_count", 0)),
            "skipped_elements": inventory.get("skipped_elements", [])
        }

        return answer, valid_regions, visual_inventory

    except (json.JSONDecodeError, ValueError, TypeError):
        return raw_response.strip(), [], empty_inventory

