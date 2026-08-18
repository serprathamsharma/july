import time
import httpx
import base64
from typing import Dict, Any, Optional
from backend.config.settings import settings

class SarvamTTSProvider:
    """
    Integrates with Sarvam AI Text-to-Speech (TTS) API (Bulbul v1)
    to synthesize high-fidelity natural speech responses in Indic & Indian-English languages.
    """
    # Mapping Indic language codes to optimal Sarvam Bulbul v1 voice profiles
    LANGUAGE_VOICE_MAP = {
        "en-IN": "meera",
        "hi-IN": "arvind",
        "ta-IN": "kavitha",
        "te-IN": "kavya",
        "bn-IN": "ananya",
        "kn-IN": "shruti",
        "ml-IN": "reshma",
        "gu-IN": "pooja",
        "mr-IN": "aarohi",
        "pa-IN": "gurpreet",
        "or-IN": "archana"
    }

    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.endpoint = settings.SARVAM_TTS_URL
        self.default_speaker = settings.SARVAM_TTS_SPEAKER
        self._cache: Dict[str, str] = {}  # (text_hash, lang) -> base64 audio

    def resolve_speaker(self, language_code: str, speaker_override: Optional[str] = None) -> str:
        """Determines best voice speaker profile based on language code and overrides."""
        if speaker_override:
            return speaker_override
        return self.LANGUAGE_VOICE_MAP.get(language_code, self.default_speaker)

    async def synthesize(
        self,
        text: str,
        target_language_code: str = "en-IN",
        speaker: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes text into base64 WAV audio.
        Returns: {
            "audio_base64": str,
            "language_code": str,
            "speaker": str,
            "duration_ms": float,
            "cached": bool,
            "provider": str
        }
        """
        if not text or not text.strip():
            return {"error": "Empty text provided for synthesis", "audio_base64": None}

        # Truncate to first 500 characters for snappy voice playback
        clean_text = text.strip()
        if len(clean_text) > 500:
            clean_text = clean_text[:497] + "..."

        speaker_name = self.resolve_speaker(target_language_code, speaker)
        cache_key = f"{clean_text}_{target_language_code}_{speaker_name}"

        if cache_key in self._cache:
            return {
                "audio_base64": self._cache[cache_key],
                "language_code": target_language_code,
                "speaker": speaker_name,
                "duration_ms": 0.5,
                "cached": True,
                "provider": "sarvam_tts_cache"
            }

        # Check API key configuration
        has_key = bool(self.api_key and not self.api_key.startswith("your_"))
        
        t_start = time.perf_counter()
        if has_key:
            try:
                headers = {
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "inputs": [clean_text],
                    "target_language_code": target_language_code,
                    "speaker": speaker_name,
                    "pitch": 0,
                    "pace": 1.05,
                    "loudness": 1.5,
                    "speech_sample_rate": 22050,
                    "enable_preprocessing": True,
                    "model": "bulbul:v1"
                }

                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self.endpoint, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        audios = data.get("audios", [])
                        if audios:
                            audio_b64 = audios[0]
                            self._cache[cache_key] = audio_b64
                            latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
                            return {
                                "audio_base64": audio_b64,
                                "language_code": target_language_code,
                                "speaker": speaker_name,
                                "duration_ms": latency_ms,
                                "cached": False,
                                "provider": "sarvam_ai"
                            }
            except Exception as e:
                print(f"[SarvamTTS] API call failed: {e}. Falling back to browser speech synthesis.")

        # Fallback: Indicate to client to use high-fidelity Web Speech API
        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "audio_base64": None,
            "language_code": target_language_code,
            "speaker": speaker_name,
            "duration_ms": latency_ms,
            "cached": False,
            "provider": "browser_speech_fallback"
        }

    def _generate_fallback_wav(self, text: str) -> bytes:
        """Generates a valid lightweight PCM WAV header binary."""
        import struct
        sample_rate = 16000
        num_samples = min(int(sample_rate * 1.5), 24000)
        data_size = num_samples * 2
        
        # Build 44-byte standard RIFF WAV header
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + data_size,
            b'WAVE',
            b'fmt ',
            16,
            1,  # PCM
            1,  # 1 channel (mono)
            sample_rate,
            sample_rate * 2,
            2,  # block align
            16, # bits per sample
            b'data',
            data_size
        )
        silence = b'\x00\x00' * num_samples
        return header + silence
