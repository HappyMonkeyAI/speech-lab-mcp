from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from speech_lab_mcp.config import Settings, load_settings
from speech_lab_mcp.lab import SpeechLab, dumps_pretty

mcp = FastMCP(
    "speech-lab",
    instructions=(
        "SpeechLab synthesizes speech to WAV files on disk and returns absolute paths. "
        "Use list_providers / provider_status to see what is healthy, list_voices for "
        "voice ids, then synthesize(text, provider?, voice?). Copy the WAV into your "
        "game or video project as needed. Woof audio should credit 'Voice by Underdog Woof'."
    ),
)

_lab: SpeechLab | None = None


def get_lab() -> SpeechLab:
    global _lab
    if _lab is None:
        _lab = SpeechLab(load_settings())
    return _lab


def configure_lab(settings: Settings | None = None, lab: SpeechLab | None = None) -> SpeechLab:
    global _lab
    if lab is not None:
        _lab = lab
        return _lab
    _lab = SpeechLab(settings or load_settings())
    return _lab


@mcp.tool()
async def list_providers() -> str:
    """List configured TTS providers and whether each is currently healthy."""
    rows = await get_lab().list_providers()
    return dumps_pretty(rows)


@mcp.tool()
async def provider_status(provider: str | None = None) -> str:
    """Health-check one provider, or all configured providers when omitted."""
    statuses = await get_lab().provider_status(provider)
    payload = [
        {
            "name": s.name,
            "configured": s.configured,
            "healthy": s.healthy,
            "latency_ms": s.latency_ms,
            "error": s.error,
            "details": s.details,
        }
        for s in statuses
    ]
    return dumps_pretty(payload)


@mcp.tool()
async def list_voices(provider: str | None = None) -> str:
    """List voices for one provider, or all configured providers when omitted."""
    voices = await get_lab().list_voices(provider)
    return dumps_pretty(voices)


@mcp.tool()
async def synthesize(
    text: str,
    provider: str | None = None,
    voice: str | None = None,
    filename_hint: str | None = None,
) -> str:
    """Synthesize speech to a WAV file and return its absolute path plus metadata.

    Args:
        text: Spoken line to generate.
        provider: piper | pocket | woof | cartesia (default from env / first healthy local).
        voice: Provider-specific voice id or name (Pocket also accepts an audio prompt URL).
        filename_hint: Optional short label included in the output filename.
    """
    result = await get_lab().synthesize(
        text,
        provider=provider,
        voice=voice,
        filename_hint=filename_hint,
    )
    return dumps_pretty(result)


def run_server(settings: Settings | None = None) -> None:
    cfg = settings or load_settings()
    configure_lab(cfg)
    # mcp 1.x binds host/port/http flags on the FastMCP settings object.
    mcp.settings.host = cfg.host
    mcp.settings.port = cfg.port
    transport = cfg.transport
    if transport == "stdio":
        mcp.run(transport="stdio")
        return
    if transport == "streamable-http":
        mcp.settings.stateless_http = True
        mcp.settings.json_response = True
        mcp.run(transport="streamable-http")
        return
    if transport == "sse":
        # Legacy transport for older clients; prefer streamable-http for new work.
        mcp.run(transport="sse")
        return
    raise ValueError(f"Unsupported SPEECH_LAB_TRANSPORT={transport!r}")
