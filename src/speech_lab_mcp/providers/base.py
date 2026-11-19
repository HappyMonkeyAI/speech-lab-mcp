from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class VoiceInfo:
    id: str
    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    configured: bool
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SynthesisResult:
    audio: bytes
    voice: str
    content_type: str = "audio/wav"
    credit: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TtsProvider(Protocol):
    name: str
    kind: str  # local | cloud

    async def health(self) -> ProviderStatus: ...

    async def list_voices(self) -> list[VoiceInfo]: ...

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> SynthesisResult: ...

    async def aclose(self) -> None: ...
