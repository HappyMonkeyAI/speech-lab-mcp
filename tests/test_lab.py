from pathlib import Path

import pytest

from speech_lab_mcp.audio import pcm16le_to_wav
from speech_lab_mcp.config import Settings
from speech_lab_mcp.lab import SpeechLab
from speech_lab_mcp.providers.base import ProviderStatus, SynthesisResult, VoiceInfo


class FakeProvider:
    name = "fake"
    kind = "local"

    async def health(self) -> ProviderStatus:
        return ProviderStatus(name=self.name, configured=True, healthy=True, latency_ms=1.0)

    async def list_voices(self) -> list[VoiceInfo]:
        return [VoiceInfo(id="advisor-a", name="Advisor A")]

    async def synthesize(self, text: str, *, voice: str | None = None) -> SynthesisResult:
        audio = pcm16le_to_wav(b"\x00\x00" * 80, sample_rate=16000)
        return SynthesisResult(audio=audio, voice=voice or "advisor-a")

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_lab_synthesize_writes_wav(tmp_path: Path):
    settings = Settings(
        output_dir=tmp_path,
        piper_url=None,
        pocket_url=None,
        woof_url=None,
        cartesia_api_key=None,
        default_provider="fake",
    )
    lab = SpeechLab(settings, providers={"fake": FakeProvider()})
    result = await lab.synthesize("Welcome to Arc Prominence.", voice="advisor-a")
    path = Path(result["path"])
    assert path.exists()
    assert path.suffix == ".wav"
    assert path.read_bytes()[:4] == b"RIFF"
    assert result["provider"] == "fake"
    assert result["voice"] == "advisor-a"
    await lab.aclose()


@pytest.mark.asyncio
async def test_list_providers_and_voices(tmp_path: Path):
    settings = Settings(output_dir=tmp_path)
    lab = SpeechLab(settings, providers={"fake": FakeProvider()})
    providers = await lab.list_providers()
    assert providers[0]["name"] == "fake"
    assert providers[0]["healthy"] is True
    voices = await lab.list_voices("fake")
    assert voices["fake"][0]["id"] == "advisor-a"
    await lab.aclose()
