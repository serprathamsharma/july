import time
import httpx
from typing import Dict, Any, Optional
from backend.stt.base import BaseSTTProvider
from backend.config.settings import settings

class SarvamSTTProvider(BaseSTTProvider):
    """
    Sarvam AI Speech-to-Text Integration
    """
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or settings.SARVAM_API_KEY
        self.api_url = api_url or settings.SARVAM_STT_URL

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", language_code: Optional[str] = "en-IN") -> Dict[str, Any]:
        start = time.perf_counter()
        
        if not self.api_key or self.api_key.startswith("your_"):
            # Fallback mock for audio byte processing when key is absent
            stt_ms = (time.perf_counter() - start) * 1000 + 15.0
            return {
                "text": "What are the primary factors influencing economic growth in India?",
                "confidence": 0.92,
                "language": language_code or "en-IN",
                "stt_ms": round(stt_ms, 2),
                "provider": "sarvam_simulated",
                "warning": "SARVAM_API_KEY not configured; using simulated STT output."
            }

        headers = {
            "api-subscription-key": self.api_key
        }

        files = {
            "file": (filename, audio_bytes, "audio/wav")
        }

        data = {
            "model": "saaras:v1",
            "language_code": language_code or "hi-IN",
            "with_timestamps": "false"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, headers=headers, files=files, data=data)
                stt_ms = (time.perf_counter() - start) * 1000
                
                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("transcript", result.get("text", ""))
                    return {
                        "text": transcript,
                        "confidence": result.get("confidence", 0.95),
                        "language": result.get("language_code", language_code),
                        "stt_ms": round(stt_ms, 2),
                        "provider": "sarvam"
                    }
                else:
                    return {
                        "text": "",
                        "confidence": 0.0,
                        "error": f"Sarvam API HTTP {response.status_code}: {response.text}",
                        "stt_ms": round(stt_ms, 2),
                        "provider": "sarvam"
                    }
        except Exception as e:
            stt_ms = (time.perf_counter() - start) * 1000
            return {
                "text": "",
                "confidence": 0.0,
                "error": f"Sarvam STT Exception: {str(e)}",
                "stt_ms": round(stt_ms, 2),
                "provider": "sarvam"
            }
