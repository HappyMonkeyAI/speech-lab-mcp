from speech_lab_mcp.audio import make_output_path, pcm16le_to_wav, slugify, write_wav


def test_pcm16le_to_wav_has_riff_header():
    pcm = b"\x00\x00" * 100
    wav = pcm16le_to_wav(pcm, sample_rate=16000)
    assert wav[:4] == b"RIFF"
    assert b"WAVE" in wav[:16]


def test_slugify_and_output_path(tmp_path):
    assert slugify("Hello, Advisor!") == "hello-advisor"
    path = make_output_path(tmp_path, provider="piper", voice="alba", text="Welcome home")
    assert path.parent == tmp_path
    assert path.suffix == ".wav"
    assert "piper" in path.name
    assert "alba" in path.name


def test_write_wav(tmp_path):
    target = tmp_path / "clip.wav"
    written = write_wav(target, b"RIFF....")
    assert written.exists()
    assert written.read_bytes() == b"RIFF...."
