from __future__ import annotations

import time
from typing import Any

import httpx

from speech_lab_mcp.providers.base import ProviderStatus, SynthesisResult, VoiceInfo


class HttpSpeakProvider:
    """Adapter for Piper/Woof-style APIs: /health, /voices, POST /speak → WAV."""

    kind = "local"

    def __init__(
        self,
        name: str,
        base_url: str,
        *,
        timeout_s: float = 60.0,
        max_wav_bytes: int = 50 * 1024 * 1024,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.max_wav_bytes = max_wav_bytes
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
                details = {"raw": response.text[:200]}
            return ProviderStatus(
                name=self.name,
                configured=True,
                healthy=True,
                latency_ms=latency,
                details=details if isinstance(details, dict) else {"body": details},
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
        response = await self._client.get(f"{self.base_url}/voices")
        response.raise_for_status()
        payload = response.json()
        voices = payload.get("voices") if isinstance(payload, dict) else payload
        default = payload.get("default") if isinstance(payload, dict) else None
        credit = payload.get("credit") if isinstance(payload, dict) else None
        result: list[VoiceInfo] = []
        if isinstance(voices, list):
            for item in voices:
                if isinstance(item, str):
                    result.append(
                        VoiceInfo(
                            id=item,
                            name=item,
                            metadata={
                                "default": item == default,
                                **({"credit": credit} if credit else {}),
                            },
                        )
                    )
                elif isinstance(item, dict) and item.get("id"):
                    result.append(
                        VoiceInfo(
                            id=str(item["id"]),
                            name=item.get("name"),
                            description=item.get("description"),
                            metadata={k: v for k, v in item.items() if k not in {"id", "name", "description"}},
                        )
                    )
        return result

    async def synthesize(self, text: str, *, voice: str | None = None) -> SynthesisResult:
        spoken = text.strip()
        if not spoken:
            raise ValueError("text must not be empty")
        body: dict[str, Any] = {"text": spoken}
        if voice:
            body["voice"] = voice
        response = await self._client.post(f"{self.base_url}/speak", json=body)
        if response.status_code >= 400:
            raise RuntimeError(
                f"{self.name} synthesize failed: HTTP {response.status_code} {response.text[:300]}"
            )
        data = response.content
        if not data:
            raise RuntimeError(f"{self.name} returned empty audio")
        if len(data) > self.max_wav_bytes:
            raise RuntimeError(f"{self.name} WAV exceeded max size ({self.max_wav_bytes} bytes)")
        content_type = (response.headers.get("content-type") or "audio/wav").split(";", 1)[0].strip()
        used_voice = response.headers.get("x-voice") or voice or "default"
        credit = response.headers.get("x-credit")
        return SynthesisResult(
            audio=data,
            voice=used_voice,
            content_type=content_type,
            credit=credit,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
