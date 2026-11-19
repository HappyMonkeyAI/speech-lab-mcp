import httpx
import pytest
import respx

from speech_lab_mcp.providers.http_speak import HttpSpeakProvider
from speech_lab_mcp.providers.pocket import PocketProvider


MINIMAL_WAV = (
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
    b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
)


@pytest.mark.asyncio
@respx.mock
async def test_piper_like_health_voices_speak():
    base = "http://piper.test"
    respx.get(f"{base}/health").mock(
        return_value=httpx.Response(200, json={"status": "ok", "voices": ["en_GB-alba-medium"]})
    )
    respx.get(f"{base}/voices").mock(
        return_value=httpx.Response(
            200, json={"default": "en_GB-alba-medium", "voices": ["en_GB-alba-medium", "en_US-lessac-medium"]}
        )
    )
    respx.post(f"{base}/speak").mock(
        return_value=httpx.Response(
            200,
            content=MINIMAL_WAV,
            headers={"content-type": "audio/wav", "x-voice": "en_GB-alba-medium"},
        )
    )

    provider = HttpSpeakProvider("piper", base)
    status = await provider.health()
    assert status.healthy is True
    voices = await provider.list_voices()
    assert [v.id for v in voices] == ["en_GB-alba-medium", "en_US-lessac-medium"]
    result = await provider.synthesize("Hello advisors", voice="en_GB-alba-medium")
    assert result.audio == MINIMAL_WAV
    assert result.voice == "en_GB-alba-medium"
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_pocket_form_tts():
    base = "http://pocket.test"
    respx.get(f"{base}/health").mock(return_value=httpx.Response(200, json={"ok": True}))
    route = respx.post(f"{base}/tts").mock(
        return_value=httpx.Response(200, content=MINIMAL_WAV, headers={"content-type": "audio/wav"})
    )

    provider = PocketProvider(base, default_voice="alba")
    result = await provider.synthesize("Line one", voice="cosette")
    assert result.audio.startswith(b"RIFF")
    assert route.called
    sent = route.calls.last.request
    assert "cosette" in sent.content.decode()
    await provider.aclose()
