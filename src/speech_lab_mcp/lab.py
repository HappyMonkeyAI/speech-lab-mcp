from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from speech_lab_mcp.audio import make_output_path, write_wav
from speech_lab_mcp.config import Settings
from speech_lab_mcp.providers.base import ProviderStatus, TtsProvider, VoiceInfo
from speech_lab_mcp.providers.registry import build_registry


class SpeechLab:
    def __init__(
        self,
        settings: Settings,
        providers: dict[str, TtsProvider] | None = None,
    ) -> None:
        self.settings = settings
        self.output_dir = settings.ensure_output_dir()
        self.providers = providers if providers is not None else build_registry(settings)

    def configured_names(self) -> list[str]:
        return sorted(self.providers.keys())

    def get_provider(self, name: str) -> TtsProvider:
        key = name.strip().lower()
        if key not in self.providers:
            available = ", ".join(self.configured_names()) or "(none)"
            raise KeyError(f"Unknown or unconfigured provider '{name}'. Available: {available}")
        return self.providers[key]

    def resolve_provider_name(self, provider: str | None) -> str:
        if provider and provider.strip():
            return provider.strip().lower()
        if self.settings.default_provider and self.settings.default_provider in self.providers:
            return self.settings.default_provider
        names = self.configured_names()
        if not names:
            raise RuntimeError(
                "No TTS providers configured. Set SPEECH_LAB_PIPER_URL / "
                "SPEECH_LAB_POCKET_URL / SPEECH_LAB_WOOF_URL and/or CARTESIA_API_KEY."
            )
        # Prefer local engines for default.
        for preferred in ("piper", "pocket", "woof", "cartesia"):
            if preferred in self.providers:
                return preferred
        return names[0]

    async def list_providers(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name, provider in sorted(self.providers.items()):
            status = await provider.health()
            rows.append(
                {
                    "name": name,
                    "kind": getattr(provider, "kind", "unknown"),
                    "configured": True,
                    "healthy": status.healthy,
                    "latency_ms": status.latency_ms,
                    "error": status.error,
                }
            )
        return rows

    async def provider_status(self, provider: str | None = None) -> list[ProviderStatus]:
        if provider:
            p = self.get_provider(provider)
            return [await p.health()]
        return [await p.health() for _, p in sorted(self.providers.items())]

    async def list_voices(self, provider: str | None = None) -> dict[str, list[dict[str, Any]]]:
        names = [self.resolve_provider_name(provider)] if provider else self.configured_names()
        result: dict[str, list[dict[str, Any]]] = {}
        for name in names:
            voices = await self.get_provider(name).list_voices()
            result[name] = [_voice_to_dict(v) for v in voices]
        return result

    async def synthesize(
        self,
        text: str,
        *,
        provider: str | None = None,
        voice: str | None = None,
        filename_hint: str | None = None,
    ) -> dict[str, Any]:
        spoken = text.strip()
        if not spoken:
            raise ValueError("text must not be empty")
        provider_name = self.resolve_provider_name(provider)
        engine = self.get_provider(provider_name)
        used_voice = voice or self.settings.default_voice
        result = await engine.synthesize(spoken, voice=used_voice)
        path = make_output_path(
            self.output_dir,
            provider=provider_name,
            voice=result.voice,
            text=filename_hint or spoken,
        )
        written = write_wav(path, result.audio)
        payload: dict[str, Any] = {
            "path": str(written),
            "provider": provider_name,
            "voice": result.voice,
            "bytes": len(result.audio),
            "content_type": result.content_type,
        }
        if result.credit:
            payload["credit"] = result.credit
        if result.metadata:
            payload["metadata"] = result.metadata
        return payload

    async def aclose(self) -> None:
        for provider in self.providers.values():
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()


def _voice_to_dict(voice: VoiceInfo) -> dict[str, Any]:
    data = asdict(voice)
    return data


def dumps_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)
