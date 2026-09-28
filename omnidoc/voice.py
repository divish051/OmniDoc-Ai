"""
OmniDoc AI - Multilingual Voice QA
Handles audio recorded from the microphone (via streamlit-mic-recorder)
and transcribes speech with native multilingual support (Tamil, Hindi, Tanglish, English)
using Gemini 2.0's native audio reasoning.
"""

from typing import Optional, Tuple
from google import genai
from google.genai import types


AUDIO_TRANSCRIPTION_PROMPT = """You are an expert multilingual speech-to-text transcriber specializing in Indian and regional languages and accents (including Tamil, Hindi, Tanglish, Hinglish, and English).

Listen to the audio recording carefully:
1. Accurately transcribe the spoken words into natural written text.
2. If spoken in a mix of languages (e.g., Tanglish: Tamil + English, or Hinglish: Hindi + English), transcribe accurately preserving the intent and specific terms.
3. Return ONLY the transcribed text. Do NOT add prefix notes, explanations, or quotes.
"""


def transcribe_audio_bytes(
    audio_bytes: bytes,
    api_key: str,
    mime_type: str = "audio/wav",
    model_name: str = "gemini-3.6-flash"
) -> Tuple[str, Optional[str]]:
    """
    Transcribes audio bytes using Gemini's native multimodal audio understanding.
    
    Returns:
        (transcribed_text, error_message)
    """
    if not audio_bytes:
        return "", "Empty audio recording received."
        
    try:
        client = genai.Client(api_key=api_key)
        
        # Audio part for Gemini
        audio_part = types.Part.from_bytes(
            data=audio_bytes,
            mime_type=mime_type
        )
        
        candidate_models = [model_name, "gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
        response = None
        last_err = None
        
        for candidate in candidate_models:
            try:
                response = client.models.generate_content(
                    model=candidate,
                    contents=[audio_part, AUDIO_TRANSCRIPTION_PROMPT],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=500
                    )
                )
                if response:
                    break
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "404" in err_str or "not found" in err_str or "no longer available" in err_str:
                    continue
                raise e
                
        if response is None:
            if last_err:
                raise last_err
            raise RuntimeError("Failed to transcribe audio from available Gemini models.")
        
        text = (response.text or "").strip()
        # Clean any accidental quotes
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
            
        return text, None
        
    except Exception as e:
        return "", f"Voice transcription failed: {str(e)}"
