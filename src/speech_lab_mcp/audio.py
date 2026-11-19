from __future__ import annotations

import io
import re
import wave
from datetime import datetime, timezone
from pathlib import Path


_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def pcm16le_to_wav(pcm: bytes, *, sample_rate: int, channels: int = 1) -> bytes:
    """Wrap raw PCM s16le bytes in a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buffer.getvalue()


def slugify(value: str, *, max_len: int = 48) -> str:
    cleaned = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return (cleaned or "clip")[:max_len]


def make_output_path(
    output_dir: Path,
    *,
    provider: str,
    voice: str,
    text: str,
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    preview = slugify(text[:40])
    voice_slug = slugify(voice or "default", max_len=32)
    name = f"{stamp}_{slugify(provider, max_len=16)}_{voice_slug}_{preview}.wav"
    return output_dir / name


def write_wav(path: Path, data: bytes) -> Path:
    if not data:
        raise ValueError("Refusing to write empty WAV")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path.resolve()
