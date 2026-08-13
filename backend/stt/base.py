from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSTTProvider(ABC):
    """
    Abstract interface for Speech-to-Text providers.
    Ensures STT provider can be replaced seamlessly (Sarvam, Whisper, etc.)
    """
    @abstractmethod
    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", language_code: Optional[str] = "hi-IN") -> Dict[str, Any]:
        """
        Transcribe audio bytes into text.
        Returns:
            Dict containing:
            {
                "text": "transcribed text string",
                "confidence": 0.95,
                "language": "hi-IN" or "en-IN",
                "stt_ms": 45.2,
                "provider": "sarvam"
            }
        """
        pass
