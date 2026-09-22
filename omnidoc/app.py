"""
OmniDoc AI - Streamlit Dual-Pane Application
Main interface with Visual Source Attribution, Zero-Hallucination Guardrails,
and Multilingual Voice QA.
"""

import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Load local .env
load_dotenv()

from omnidoc.styles import CUSTOM_CSS
from omnidoc.pdf_processor import extract_pdf_pages_as_images
from omnidoc.indexer import is_document_indexed, index_document
from omnidoc.qa_engine import answer_document_query
from omnidoc.voice import transcribe_audio_bytes

# Optional mic recorder
try:
    from streamlit_mic_recorder import mic_recorder
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False


st.set_page_config(
    page_title="OmniDoc AI | Multimodal Document QA",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom styling
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None
if "active_page" not in st.session_state:
    st.session_state.active_page = 1
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
if "model_name" not in st.session_state or any(bad in st.session_state.model_name.lower() for bad in ["tts", "audio", "embedding", "imagen", "aqa"]):
    st.session_state.model_name = "gemini-3.1-pro-preview"
if "annotated_image_path" not in st.session_state:
    st.session_state.annotated_image_path = None
if "bounding_boxes" not in st.session_state:
    st.session_state.bounding_boxes = []


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### ⚙️ System Controls")
    
    # API Key Input
    user_api_key = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        help="Get a free Gemini key at https://aistudio.google.com"
    )
    if user_api_key != st.session_state.api_key:
        st.session_state.api_key = user_api_key
        
    from omnidoc.model_utils import get_available_gemini_models
    live_models = get_available_gemini_models(st.session_state.api_key)
    
    # Ensure current model is valid and in live_models
    if st.session_state.model_name not in live_models and live_models:
        st.session_state.model_name = live_models[0]
        
    current_model_idx = live_models.index(st.session_state.model_name) if st.session_state.model_name in live_models else 0
    
    model_choice = st.selectbox(
        "Intelligence Engine",
        options=live_models,
        index=current_model_idx,
        help="Discovered live models supported by your Google Gemini API key."
    )
    st.session_state.model_name = model_choice

    st.markdown("---")
    st.markdown("### 📄 Document Ingestion")
    
    uploaded_file = st.file_uploader(
        "Upload Financial / Technical PDF",
        type=["pdf"],
        help="Upload earnings reports, balance sheets, medical or legal filings."
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        
        # Check if already processed
        if st.session_state.current_doc is None or st.session_state.current_doc.get("filename") != uploaded_file.name:
            with st.spinner("⚡ Slicing document pages into high-res images..."):
                doc_info = extract_pdf_pages_as_images(
                    file_bytes=file_bytes,
                    filename=uploaded_file.name
                )
                st.session_state.current_doc = doc_info
                st.session_state.active_page = 1
                st.success(f"Extracted {doc_info['total_pages']} pages as high-res images.")

    # Ensure document is indexed whenever both document and API key are present
    if st.session_state.current_doc is not None:
        doc_info = st.session_state.current_doc
        doc_id = doc_info["doc_id"]
        total_p = doc_info["total_pages"]

        if not st.session_state.api_key:
            st.warning("⚠️ Enter your Gemini API Key above to index this document.")
        else:
            if not is_document_indexed(doc_id, total_p):
                with st.spinner("Indexing pages into ChromaDB..."):
                    progress_bar = st.progress(0, text="Indexing pages into ChromaDB...")
                    
                    def on_progress(current, total, msg):
                        percent = int((current / total) * 100)
                        progress_bar.progress(percent, text=f"[{current}/{total}] {msg}")
                        
                    try:
                        index_document(
                            doc_info=doc_info,
                            api_key=st.session_state.api_key,
                            progress_callback=on_progress,
                            model_name=st.session_state.model_name
                        )
                        progress_bar.progress(100, text="Indexing complete!")
                        st.success("✅ ChromaDB Semantic Index Ready!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Indexing Error: {str(e)}")
            else:
                st.success("✅ Document is indexed in ChromaDB.")
                    
    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size:12px; color:#8b949e; line-height:1.4;">
        <b>OmniDoc AI Architecture:</b><br/>
        • <b>PyMuPDF</b>: 200 DPI Page Slicing<br/>
        • <b>ChromaDB</b>: Persistent Vector DB<br/>
        • <b>Gemini 2.0</b>: Spatial Chart Reasoning<br/>
        • <b>Guardrails</b>: Strict [DATA_MISSING] Alert
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# HEADER BANNER
# =========================================================
st.markdown(
    f"""
    <div class="omnidoc-header">
        <div>
            <div class="omnidoc-title">🚀 OmniDoc AI</div>
            <div class="omnidoc-subtitle">Multimodal Document QA with Visual Source Attribution & Zero-Hallucination Guardrails</div>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
            <span class="omnidoc-badge">⚡ {st.session_state.model_name}</span>
            <span class="omnidoc-badge" style="color:#58a6ff; border-color:rgba(56,139,253,0.4); background:rgba(56,139,253,0.15);">
                📦 ChromaDB Local
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# DUAL-PANE WORKSPACE
# =========================================================
col_source, col_chat = st.columns([1, 1], gap="medium")


# ─── LEFT PANE: VISUAL SOURCE ATTRIBUTION ───────────────
with col_source:
    st.markdown(
        """
        <div class="pane-title">
            <span>🖼️ Visual Source Attribution (Ground Truth)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    doc = st.session_state.current_doc

    if not doc or not doc.get("pages"):
        st.info("👈 Upload a PDF from the sidebar to inspect high-resolution page images.")
        # Placeholder visual frame
        st.markdown(
            """
            <div style="height:480px; display:flex; flex-direction:column; justify-content:center; align-items:center; 
                        background:rgba(22,27,34,0.4); border:2px dashed rgba(48,54,61,0.8); border-radius:12px; color:#8b949e;">
                <span style="font-size:42px;">📊</span>
                <span style="margin-top:10px; font-weight:500;">No Document Active</span>
                <span style="font-size:12px; margin-top:4px;">Upload an earnings report or table-heavy PDF to begin</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        total_p = doc["total_pages"]
        
        # Navigation header
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if st.button("◀ Prev", disabled=(st.session_state.active_page <= 1), use_container_width=True):
                st.session_state.active_page -= 1
                st.rerun()
        with nav_col2:
            page_options = list(range(1, total_p + 1))
            current_idx = page_options.index(st.session_state.active_page) if st.session_state.active_page in page_options else 0
            selected_page = st.selectbox(
                "Navigate Page",
                options=page_options,
                index=current_idx,
                format_func=lambda x: f"Page {x} of {total_p}",
                label_visibility="collapsed"
            )
            if selected_page != st.session_state.active_page:
                st.session_state.active_page = selected_page
                st.rerun()
        with nav_col3:
            if st.button("Next ▶", disabled=(st.session_state.active_page >= total_p), use_container_width=True):
                st.session_state.active_page += 1
                st.rerun()

        # Render active page image (annotated if available, original otherwise)
        active_page_data = next((p for p in doc["pages"] if p["page_num"] == st.session_state.active_page), None)
        if active_page_data and Path(active_page_data["image_path"]).exists():
            # Check if we have an annotated image for this page
            display_image_path = active_page_data["image_path"]
            has_bbox = False
            bbox_count = 0
            
            if (st.session_state.annotated_image_path 
                and Path(st.session_state.annotated_image_path).exists()
                and st.session_state.bounding_boxes):
                display_image_path = st.session_state.annotated_image_path
                has_bbox = True
                bbox_count = len(st.session_state.bounding_boxes)

            # Header with bbox indicator
            bbox_badge = ""
            if has_bbox:
                bbox_badge = f'<span style="background:rgba(0,200,255,0.15); border:1px solid rgba(0,200,255,0.5); color:#00c8ff; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:700;">🔍 {bbox_count} Evidence Region{"s" if bbox_count > 1 else ""} Highlighted</span>'
            
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; font-size:12px; color:#8b949e; flex-wrap:wrap; gap:6px;">
                    <span><b>File:</b> {doc['filename']}</span>
                    <div style="display:flex; gap:8px; align-items:center;">
                        {bbox_badge}
                        <span class="page-attribution-badge">📌 Viewing Page {st.session_state.active_page}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.image(
                display_image_path,
                use_container_width=True,
                caption=f"{doc['filename']} — Page {st.session_state.active_page}" + (" [Evidence Boundaries Shown]" if has_bbox else "")
            )
            
            # Toggle to view original (without annotations)
            if has_bbox:
                if st.button("👁️ Toggle: Show Original (No Boundaries)", key="toggle_bbox", use_container_width=True):
                    st.session_state.annotated_image_path = None
                    st.session_state.bounding_boxes = []
                    st.rerun()
        else:
            st.error("Page image is missing on disk.")


# ─── RIGHT PANE: CONVERSATIONAL QA & GUARDRAILS ─────────
with col_chat:
    st.markdown(
        """
        <div class="pane-title">
            <span>💬 Verified Document Intelligence</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Voice Input Bar
    voice_query_text = ""
    if MIC_AVAILABLE:
        st.markdown('<div class="voice-bar">🎙️ <b>Multilingual Voice QA</b> (Speak in Tamil, Hindi, Tanglish, or English)</div>', unsafe_allow_html=True)
        audio = mic_recorder(
            start_prompt="🔴 Press to Speak Question",
            stop_prompt="⏹️ Stop & Process Voice Query",
            key="mic_recorder",
            format="wav"
        )
        if audio and audio.get("bytes"):
            if not st.session_state.api_key:
                st.error("Please provide a Gemini API Key in the sidebar to process voice.")
            else:
                with st.spinner("🗣️ Transcribing speech via Gemini 2.0..."):
                    transcribed, err = transcribe_audio_bytes(
                        audio_bytes=audio["bytes"],
                        api_key=st.session_state.api_key,
                        mime_type="audio/wav",
                        model_name=st.session_state.model_name
                    )
                    if err:
                        st.error(err)
                    elif transcribed:
                        voice_query_text = transcribed
                        st.info(f"🎤 Transcribed Question: **\"{transcribed}\"**")

    # Render Conversation History
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.write(content)
            else:
                with st.chat_message("assistant", avatar="🚀"):
                    if msg.get("is_data_missing"):
                        # RED SECURITY ALERT BANNER
                        st.markdown(
                            f"""
                            <div class="security-alert-box">
                                <div class="security-alert-title">
                                    🚨 [DATA_MISSING] ZERO-HALLUCINATION GUARDRAIL TRIGGERED
                                </div>
                                <div class="security-alert-msg">
                                    <b>Security Notice:</b> The requested figure or information is not visually verifiable on the source page.<br/>
                                    <hr style="border-color:rgba(248,81,73,0.3); margin:8px 0;"/>
                                    {msg.get("missing_reason", content)}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        # VERIFIED ANSWER CARD
                        source_p = msg.get("source_page")
                        page_badge = f'<span class="page-attribution-badge">📌 Grounded in Page {source_p}</span>' if source_p else ''
                        st.markdown(
                            f"""
                            <div class="verified-answer-card">
                                <div class="answer-header">
                                    <span class="answer-tag">✓ VERIFIED BY GEMINI 2.0</span>
                                    {page_badge}
                                </div>
                                <div style="color:#e6edf3; font-size:14px; line-height:1.6;">
                                    {content}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

    # Chat Input Box
    text_query = st.chat_input("Ask about charts, tables, or financials (or use mic above)...")
    active_query = voice_query_text or text_query

    if active_query:
        if not st.session_state.current_doc:
            st.warning("⚠️ Please upload a PDF document before asking questions.")
        elif not st.session_state.api_key:
            st.warning("⚠️ Please enter your Gemini API Key in the sidebar.")
        else:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": active_query})
            
            with st.chat_message("user", avatar="👤"):
                st.write(active_query)

            # Multimodal RAG Execution
            with st.chat_message("assistant", avatar="🚀"):
                with st.spinner("🔍 Retrieving source page & performing Gemini 2.0 visual reasoning..."):
                    result = answer_document_query(
                        doc_id=st.session_state.current_doc["doc_id"],
                        query=active_query,
                        api_key=st.session_state.api_key,
                        model_name=st.session_state.model_name,
                        target_page=st.session_state.active_page if st.session_state.current_doc.get("total_pages", 0) == 1 else None,
                        doc_pages=st.session_state.current_doc.get("pages")
                    )

                source_page = result.get("source_page")
                is_missing = result.get("is_data_missing", False)
                raw_ans = result.get("answer", "")
                missing_reason = result.get("missing_reason", "")
                bounding_boxes = result.get("bounding_boxes", [])
                annotated_path = result.get("annotated_image_path")
                visual_inventory = result.get("visual_inventory", {})

                # Automatically sync Left Pane to the identified source page!
                if source_page:
                    st.session_state.active_page = source_page
                
                # Store annotated image path and bounding boxes for left pane rendering
                if annotated_path and bounding_boxes:
                    st.session_state.annotated_image_path = annotated_path
                    st.session_state.bounding_boxes = bounding_boxes
                else:
                    st.session_state.annotated_image_path = None
                    st.session_state.bounding_boxes = []

                # Build Visual Inventory Summary (used vs skipped)
                total_el = visual_inventory.get("total_elements", 0)
                used_el = visual_inventory.get("used_count", len(bounding_boxes))
                skipped_el = visual_inventory.get("skipped_count", 0)
                skipped_list = visual_inventory.get("skipped_elements", [])

                inventory_html = ""
                if total_el > 0:
                    # Stats bar
                    inventory_html += f"""
                    <div style="margin-top:12px; padding:12px 16px; background:rgba(139,148,158,0.08); border:1px solid rgba(139,148,158,0.25); border-radius:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-size:12px; font-weight:700; color:#c9d1d9; text-transform:uppercase; letter-spacing:0.5px;">📊 Visual Element Scan Report</span>
                            <span style="font-size:11px; color:#8b949e;">Page {source_page}</span>
                        </div>
                        <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:8px;">
                            <span style="background:rgba(88,166,255,0.12); color:#58a6ff; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600; border:1px solid rgba(88,166,255,0.3);">
                                📋 Total: {total_el} element{"s" if total_el != 1 else ""}
                            </span>
                            <span style="background:rgba(63,185,80,0.12); color:#3fb950; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600; border:1px solid rgba(63,185,80,0.3);">
                                ✅ Used: {used_el}
                            </span>
                            <span style="background:rgba(210,168,255,0.12); color:#d2a8ff; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600; border:1px solid rgba(210,168,255,0.3);">
                                ⏭️ Skipped: {skipped_el}
                            </span>
                        </div>
                    """
                    # Skipped elements detail list
                    if skipped_list:
                        inventory_html += '<div style="margin-top:6px; border-top:1px solid rgba(48,54,61,0.6); padding-top:8px;">'
                        inventory_html += '<div style="font-size:11px; font-weight:600; color:#f0883e; margin-bottom:6px;">⚠️ Elements NOT Used (Why):</div>'
                        for idx, skip in enumerate(skipped_list):
                            name = skip.get("name", f"Element {idx+1}")
                            reason = skip.get("reason", "Not relevant to the query")
                            inventory_html += f"""
                            <div style="display:flex; gap:8px; align-items:flex-start; margin-bottom:5px; font-size:12px; line-height:1.4;">
                                <span style="color:#f0883e; flex-shrink:0;">▸</span>
                                <div>
                                    <span style="color:#e6edf3; font-weight:600;">{name}</span>
                                    <span style="color:#8b949e;"> — {reason}</span>
                                </div>
                            </div>
                            """
                        inventory_html += '</div>'
                    inventory_html += '</div>'

                # Render response
                if is_missing:
                    st.markdown(
                        f"""
                        <div class="security-alert-box">
                            <div class="security-alert-title">
                                🚨 [DATA_MISSING] ZERO-HALLUCINATION GUARDRAIL TRIGGERED
                            </div>
                            <div class="security-alert-msg">
                                <b>Security Notice:</b> The requested figure or information is not visually verifiable on the source page.<br/>
                                <hr style="border-color:rgba(248,81,73,0.3); margin:8px 0;"/>
                                {missing_reason or raw_ans}
                            </div>
                        </div>
                        {inventory_html}
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    # Build bounding box evidence legend
                    bbox_legend = ""
                    if bounding_boxes:
                        bbox_items = "".join(
                            f'<span style="background:rgba(0,200,255,0.12); border:1px solid rgba(0,200,255,0.3); color:#00c8ff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">🔍 {b.get("label", f"Region {i+1}")}</span>'
                            for i, b in enumerate(bounding_boxes)
                        )
                        bbox_legend = f"""
                        <div style="margin-top:10px; padding:10px 14px; background:rgba(0,200,255,0.06); border:1px solid rgba(0,200,255,0.2); border-radius:8px;">
                            <div style="font-size:11px; font-weight:700; color:#00c8ff; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">📐 Evidence Boundaries (See Left Pane)</div>
                            <div style="display:flex; flex-wrap:wrap; gap:6px;">
                                {bbox_items}
                            </div>
                        </div>
                        """
                    
                    st.markdown(
                        f"""
                        <div class="verified-answer-card">
                            <div class="answer-header">
                                <span class="answer-tag">✓ VERIFIED BY GEMINI VLM</span>
                                <span class="page-attribution-badge">📌 Grounded in Page {source_page}</span>
                            </div>
                            <div style="color:#e6edf3; font-size:14px; line-height:1.6;">
                                {raw_ans}
                            </div>
                            {bbox_legend}
                            {inventory_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # Append assistant message to session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": raw_ans,
                    "is_data_missing": is_missing,
                    "missing_reason": missing_reason,
                    "source_page": source_page,
                    "bounding_boxes": bounding_boxes,
                    "visual_inventory": visual_inventory
                })
                
                # Rerun to sync the left visual attribution pane with the newly retrieved page
                st.rerun()

