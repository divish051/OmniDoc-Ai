"""
OmniDoc AI - Model Discovery & Resilient Generation Helper
Dynamically discovers live models for the user's API key and handles
cascading fallbacks, demand spikes (503), rate limits (429), and version deprecations.
"""

import time
import logging
from typing import List, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Cache discovered models in-memory per API key
_MODEL_CACHE: dict = {}


DISALLOWED_KEYWORDS = [
    "embedding", "imagen", "aqa", "tts", "audio", "chirp", 
    "realtime", "live", "computer-use", "whisper"
]

# Primary models to try (ordered by preference)
PRIMARY_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3.6-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]


def get_available_gemini_models(api_key: str) -> List[str]:
    """
    Queries Google API to discover exactly which models are supported for generateContent.
    """
    if not api_key:
        return list(PRIMARY_MODELS)
        
    cache_key = api_key[:10]
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
        
    try:
        client = genai.Client(api_key=api_key)
        discovered = []
        for m in client.models.list():
            actions = getattr(m, "supported_actions", []) or []
            if "generateContent" in actions:
                m_name = m.name.replace("models/", "")
                # Only keep conversational / visual multimodal models (exclude tts, audio-only, embedding, imagen)
                if "gemini" in m_name.lower() and not any(x in m_name.lower() for x in DISALLOWED_KEYWORDS):
                    discovered.append(m_name)
                    
        if discovered:
            # Sort: Priority models first
            top = [m for m in PRIMARY_MODELS if m in discovered]
            rest = [m for m in discovered if m not in top]
            ordered = top + rest
            _MODEL_CACHE[cache_key] = ordered
            return ordered
    except Exception as e:
        logger.warning(f"Model discovery fallback: {e}")
        
    fallback = list(PRIMARY_MODELS)
    return fallback


def generate_with_fallback(
    client: genai.Client,
    contents: list,
    preferred_model: Optional[str] = None,
    api_key: str = "",
    temperature: float = 0.0,
    max_output_tokens: int = 1500
) -> str:
    """
    Executes content generation trying preferred model first, then falling back
    through all verified visual models on any 400 (modality), 404, 503, or 429 error.
    """
    available = get_available_gemini_models(api_key)
    
    candidates = []
    # Strict filter: Never pass any model with tts or audio
    if preferred_model and not any(bad in preferred_model.lower() for bad in DISALLOWED_KEYWORDS):
        candidates.append(preferred_model)
        
    for m in PRIMARY_MODELS + available:
        if m and m not in candidates and not any(bad in m.lower() for bad in DISALLOWED_KEYWORDS):
            candidates.append(m)
            
    last_err = None
    
    for model_name in candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens
                )
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            logger.warning(f"Model {model_name} failed: {e}. Trying next candidate...")
            # If critical auth error, raise immediately
            if "api_key_invalid" in err_str or "api key not valid" in err_str:
                raise e
            time.sleep(0.5)
            continue
                
    if last_err:
        raise last_err
    raise RuntimeError("No visual model was able to process the request.")
