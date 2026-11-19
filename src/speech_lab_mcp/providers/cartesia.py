from __future__ import annotations

import time
from typing import Any

from speech_lab_mcp.audio import pcm16le_to_wav
from speech_lab_mcp.providers.base import ProviderStatus, SynthesisResult, VoiceInfo


class CartesiaProvider:
    """Cartesia Sonic cloud TTS; writes WAV via PCM wrap (or native wav when available)."""

    name = "cartesia"
    kind = "cloud"

    def __init__(
        self,
        api_key: str,
        *,
        default_voice_id: str | None = None,
        model_id: str = "sonic-3.5",
        sample_rate: int = 24000,
        client: Any | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("CARTESIA_API_KEY is required")
        self.api_key = api_key
        self.default_voice_id = default_voice_id
        self.model_id = model_id
        self.sample_rate = sample_rate
        self._client = client

    def _ensure_client(self) -> Any:
        if self._client is None:
            from cartesia import AsyncCartesia

            self._client = AsyncCartesia(api_key=self.api_key)
        return self._client

    async def health(self) -> ProviderStatus:
        started = time.perf_counter()
        if not self.api_key and self._client is None:
            return ProviderStatus(
                name=self.name,
                configured=False,
                healthy=False,
                error="CARTESIA_API_KEY not set",
            )
        try:
            client = self._ensure_client()
            # Lightweight call: list a page of voices if the SDK supports it.
            if hasattr(client, "voices") and hasattr(client.voices, "list"):
                await client.voices.list()
            latency = (time.perf_counter() - started) * 1000
            return ProviderStatus(
                name=self.name,
                configured=True,
                healthy=True,
                latency_ms=latency,
                details={
                    "model_id": self.model_id,
                    "default_voice_id": self.default_voice_id,
                    "sample_rate": self.sample_rate,
                },
            )
        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000
            return ProviderStatus(
                name=self.name,
                configured=True,
                healthy=False,
                latency_ms=latency,
                error=str(exc),
            )

    async def list_voices(self) -> list[VoiceInfo]:
        client = self._ensure_client()
        voices: list[VoiceInfo] = []
        if self.default_voice_id:
            voices.append(
                VoiceInfo(
                    id=self.default_voice_id,
                    name="default",
                    description="Configured CARTESIA_VOICE_ID",
                    metadata={"default": True},
                )
            )
        try:
            if hasattr(client, "voices") and hasattr(client.voices, "list"):
                listed = await client.voices.list()
                items = listed if isinstance(listed, list) else getattr(listed, "voices", None) or []
                for item in items:
                    voice_id = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
                    if not voice_id:
                        continue
                    name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else None)
                    if any(v.id == voice_id for v in voices):
                        continue
                    voices.append(VoiceInfo(id=str(voice_id), name=name))
        except Exception:
            # Fall back to configured default only.
            pass
        return voices

    async def synthesize(self, text: str, *, voice: str | None = None) -> SynthesisResult:
        spoken = text.strip()
        if not spoken:
            raise ValueError("text must not be empty")
        voice_id = voice or self.default_voice_id
        if not voice_id:
            raise ValueError("Cartesia voice id is required (pass voice= or set CARTESIA_VOICE_ID)")

        client = self._ensure_client()
        # Prefer WAV container when the API accepts it; otherwise wrap PCM.
        try:
            stream = await client.tts.bytes(
                model_id=self.model_id,
                transcript=spoken,
                voice={"mode": "id", "id": voice_id},
                output_format={
                    "container": "wav",
                    "encoding": "pcm_s16le",
                    "sample_rate": self.sample_rate,
                },
            )
            chunks: list[bytes] = []
            async for chunk in stream:
                if chunk:
                    chunks.append(chunk)
            audio = b"".join(chunks)
            if audio[:4] == b"RIFF":
                return SynthesisResult(audio=audio, voice=voice_id, metadata={"model": self.model_id})
        except Exception:
            audio = b""

        stream = await client.tts.bytes(
            model_id=self.model_id,
            transcript=spoken,
            voice={"mode": "id", "id": voice_id},
            output_format={
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": self.sample_rate,
            },
        )
        chunks = []
        async for chunk in stream:
            if chunk:
                chunks.append(chunk)
        pcm = b"".join(chunks)
        if not pcm:
            raise RuntimeError("Cartesia returned empty audio")
        wav = pcm16le_to_wav(pcm, sample_rate=self.sample_rate)
        return SynthesisResult(
            audio=wav,
            voice=voice_id,
            metadata={"model": self.model_id, "sample_rate": self.sample_rate},
        )

    async def aclose(self) -> None:
        client = self._client
        if client is not None and hasattr(client, "close"):
            close = client.close
            result = close()
            if hasattr(result, "__await__"):
                await result
