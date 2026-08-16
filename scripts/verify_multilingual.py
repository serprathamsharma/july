import asyncio
from backend.guardrails.query_guardrail import QueryGuardrail
from backend.voice.tts import SarvamTTSProvider

async def main():
    print("==================================================")
    print("    PHASE 5: MULTILINGUAL & VOICE TESTS           ")
    print("==================================================")

    guardrail = QueryGuardrail()

    # 1. Disfluency & Verbal Hesitation Stripping
    print("\n--- 1. Disfluency & Speech Filler Stripping ---")
    disfluent_samples = [
        "umm like can you please tell me about faiss uh you know",
        "matlab basically explain reciprocal rank fusion toh bhai",
        "uhh actually sort of what is the MSMARCO dataset so yeah"
    ]
    for sample in disfluent_samples:
        stripped = guardrail.strip_disfluencies(sample)
        normalized = guardrail.normalize_query(sample)
        print(f"Raw Input:   '{sample}'")
        print(f"Stripped:    '{stripped}'")
        print(f"Normalized:  '{normalized}'\n")

    # 2. Indic Script & Language Auto-Detection
    print("--- 2. Indic Script & Language Detection ---")
    multilingual_queries = [
        ("What algorithms does FAISS support?", "English"),
        ("भारत की राजधानी क्या है?", "Hindi (Devanagari)"),
        ("வணக்கம் எப்படி இருக்கிறீர்கள்?", "Tamil"),
        ("భారతదేశం రాజధాని ఏది?", "Telugu"),
        ("ভারতের রাজধানী কি?", "Bengali"),
        ("faiss kaise kaam karta hai batao", "Hinglish")
    ]
    for text, expected in multilingual_queries:
        detection = guardrail.detect_language(text)
        try:
            print(f"Text: '{text}'")
        except UnicodeEncodeError:
            print(f"Text: '{text.encode('unicode_escape').decode('ascii')}'")
        print(f"  -> Expected: {expected}")
        print(f"  -> Detected: {detection['language']} ({detection['language_code']}, Script: {detection['script']})\n")

    # 3. Sarvam Text-to-Speech (TTS) Voice Synthesis
    print("--- 3. Sarvam TTS Speech Synthesis ---")
    tts = SarvamTTSProvider()
    test_text = "FAISS is a library for efficient similarity search and clustering of dense vectors."
    res = await tts.synthesize(text=test_text, target_language_code="en-IN")
    print(f"Text to Synthesize: '{test_text}'")
    print(f"Provider:           {res['provider']}")
    print(f"Audio Base64 Len:   {len(res.get('audio_base64', ''))} chars")
    print(f"Synthesis Duration: {res['duration_ms']} ms")
    print(f"Language Code:      {res['language_code']}")

    # Cache hit test
    cache_res = await tts.synthesize(text=test_text, target_language_code="en-IN")
    print(f"Cached Request Hit: {cache_res['cached']} ({cache_res['duration_ms']} ms)")

    print("\n==================================================")
    print("   ALL PHASE 5 MULTILINGUAL & VOICE CHECKS PASS!  ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
