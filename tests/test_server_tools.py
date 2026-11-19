import pytest

from speech_lab_mcp.audio import pcm16le_to_wav
from speech_lab_mcp.config import Settings
from speech_lab_mcp.lab import SpeechLab
from speech_lab_mcp.providers.base import ProviderStatus, SynthesisResult, VoiceInfo
from speech_lab_mcp import server


class FakeProvider:
    name = "fake"
    kind = "local"

    async def health(self) -> ProviderStatus:
        return ProviderStatus(name=self.name, configured=True, healthy=True, latency_ms=1.0)

    async def list_voices(self) -> list[VoiceInfo]:
        return [VoiceInfo(id="mira")]

    async def synthesize(self, text: str, *, voice: str | None = None) -> SynthesisResult:
        return SynthesisResult(
            audio=pcm16le_to_wav(b"\x00\x00" * 40, sample_rate=16000),
            voice=voice or "mira",
        )

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_tool_synthesize(tmp_path, monkeypatch):
    settings = Settings(output_dir=tmp_path)
    lab = SpeechLab(settings, providers={"fake": FakeProvider()})
    server.configure_lab(lab=lab)

    payload = await server.synthesize("Advisor briefing.", provider="fake", voice="mira")
    assert '"path"' in payload
    assert "mira" in payload
