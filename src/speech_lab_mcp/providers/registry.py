from __future__ import annotations

from typing import Any

from speech_lab_mcp.config import Settings
from speech_lab_mcp.providers.base import TtsProvider
from speech_lab_mcp.providers.cartesia import CartesiaProvider
from speech_lab_mcp.providers.http_speak import HttpSpeakProvider
from speech_lab_mcp.providers.pocket import PocketProvider


def build_registry(settings: Settings) -> dict[str, Any]:
    """Build configured providers. Unconfigured engines are omitted."""
    providers: dict[str, TtsProvider] = {}

    if settings.piper_url:
        providers["piper"] = HttpSpeakProvider(
            "piper",
            settings.piper_url,
            timeout_s=settings.http_timeout_s,
            max_wav_bytes=settings.max_wav_bytes,
        )

    if settings.pocket_url:
        providers["pocket"] = PocketProvider(
            settings.pocket_url,
            timeout_s=settings.http_timeout_s,
            max_wav_bytes=settings.max_wav_bytes,
            default_voice=settings.default_voice if settings.default_provider == "pocket" else "alba",
        )

    if settings.woof_url:
        providers["woof"] = HttpSpeakProvider(
            "woof",
            settings.woof_url,
            timeout_s=settings.http_timeout_s,
            max_wav_bytes=settings.max_wav_bytes,
        )

    if settings.cartesia_api_key:
        providers["cartesia"] = CartesiaProvider(
            settings.cartesia_api_key,
            default_voice_id=settings.cartesia_voice_id,
            model_id=settings.cartesia_model_id,
            sample_rate=settings.cartesia_sample_rate,
        )

    return providers
