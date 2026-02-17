# adapters/

External service integrations. Each adapter wraps a third-party API behind a simple function interface and returns a typed dataclass result.

All adapters gracefully degrade when `OPENAI_API_KEY` is not set, returning stub responses for local development.

## Files

- **openai_llm.py** — `extract_medical()` and `generate_followup()`. Schema-driven extraction via `gpt-4o-mini` with JSON response format. Falls back to deterministic extraction.
- **openai_stt.py** — `transcribe()`. Audio bytes to text via OpenAI transcription API.
- **openai_tts.py** — `synthesize()`. Text to base64-encoded MP3 audio via OpenAI TTS API.
