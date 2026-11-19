from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from speech_lab_mcp.providers.base import ProviderStatus, SynthesisResult, VoiceInfo

# Built-in Pocket TTS prompt names (miso / kyutai pocket serve).
POCKET_BUILTIN_VOICES = [
    "alba",
    "cosette",
    "charles",
    "anna",
    "jean",
    "marius",
    "azelma",
    "george",
    "jane",
    "eve",
]


class PocketProvider:
    """Pocket TTS: GET /health, form POST /tts (text, voice_url) → streamed WAV."""

    name = "pocket"
    kind = "local"

    def __init__(
        self,
        base_url: str,
        *,
        timeout_s: float = 60.0,
        max_wav_bytes: int = 50 * 1024 * 1024,
        default_voice: str | None = "alba",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.max_wav_bytes = max_wav_bytes
        self.default_voice = default_voice
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout_s)

    async def health(self) -> ProviderStatus:
        started = time.perf_counter()
        try:
            response = await self._client.get(f"{self.base_url}/health")
            latency = (time.perf_counter() - started) * 1000
            if response.status_code >= 400:
                return ProviderStatus(
                    name=self.name,
                    configured=True,
                    healthy=False,
                    latency_ms=latency,
                    error=f"HTTP {response.status_code}",
                )
            details: dict[str, Any] = {}
            try:
                details = response.json()
            except Exception:
                details = {}
            return ProviderStatus(
                name=self.name,
                configured=True,
                healthy=True,
                latency_ms=latency,
                details=details if isinstance(details, dict) else {},
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
        # Pocket serve may not expose /voices; return known builtins + note clone via URL.
        voices = [
            VoiceInfo(
                id=name,
                name=name,
                description="Built-in Pocket TTS voice prompt",
                metadata={"default": name == self.default_voice},
            )
            for name in POCKET_BUILTIN_VOICES
        ]
        voices.append(
            VoiceInfo(
                id="http://…/prompt.wav",
                name="custom voice_url",
                description="Pass an audio prompt URL as the voice to clone-style synthesize",
                metadata={"clone": True},
            )
        )
        return voices

    def _resolve_voice_url(self, voice: str | None) -> str | None:
        if voice is None or not voice.strip():
            return self.default_voice
        value = voice.strip()
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https", "file"}:
            return value
        return value  # built-in prompt name

    async def synthesize(self, text: str, *, voice: str | None = None) -> SynthesisResult:
        spoken = text.strip()
        if not spoken:
            raise ValueError("text must not be empty")
        form: dict[str, str] = {"text": spoken}
        voice_url = self._resolve_voice_url(voice)
        if voice_url:
            form["voice_url"] = voice_url

        response = await self._client.post(f"{self.base_url}/tts", data=form)
        if response.status_code >= 400:
            raise RuntimeError(
                f"pocket synthesize failed: HTTP {response.status_code} {response.text[:300]}"
            )
        data = response.content
        if not data:
            raise RuntimeError("pocket returned empty audio")
        if len(data) > self.max_wav_bytes:
            raise RuntimeError(f"pocket WAV exceeded max size ({self.max_wav_bytes} bytes)")
        content_type = (response.headers.get("content-type") or "audio/wav").split(";", 1)[0].strip()
        return SynthesisResult(
            audio=data,
            voice=voice_url or "default",
            content_type=content_type,
            metadata={"engine": "pocket-tts"},
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
