# SpeechLab MCP

**HappyMonkeyAI** text-to-speech lab for agents, games, and video studios.

SpeechLab exposes an [MCP](https://modelcontextprotocol.io/) server that can synthesize speech through local engines (Piper, Pocket TTS, Underdog Woof) and optionally Cartesia cloud voices. Clips are written as **WAV files** on disk; tools return **absolute paths** so an agent can copy them into a game or video project.

Copyright © 2026 Stephen Phillips / HappyMonkeyAI. Released under the [MIT License](LICENSE).

## Providers

| Provider | Kind | Notes |
|----------|------|--------|
| **piper** | local | Piper HTTP (`/voices`, `/speak`) |
| **pocket** | local | Pocket TTS (`POST /tts` form) |
| **woof** | local | Underdog Woof (`/speak`) — credit *Voice by Underdog Woof* |
| **cartesia** | cloud | Cartesia Sonic (requires `CARTESIA_API_KEY`) |

Miso GPU quality is planned as a later Compose profile.

## MCP tools

| Tool | Purpose |
|------|---------|
| `list_providers` | Configured engines + health |
| `provider_status` | Detailed health for one or all |
| `list_voices` | Voice ids per provider |
| `synthesize` | `text` + optional `provider` / `voice` / `filename_hint` → `{ path, provider, voice, bytes, ... }` |

## Security

- Copy `.env.example` → `.env` locally. **Never commit `.env`.**
- Leave `CARTESIA_API_KEY` empty unless you need cloud TTS.
- Compose publishes MCP/TTS ports on **loopback** (`127.0.0.1`) by default.
- Generated WAVs under `data/out/` are gitignored.

## Quick start (local stdio)

```bash
git clone https://github.com/HappyMonkeyAI/speech-lab-mcp.git
cd speech-lab-mcp
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env   # Windows: copy .env.example .env
```

Point provider URLs in `.env` at running engines, or start Compose (below), then:

```bash
speech-lab-mcp --transport stdio
```

### Cursor `mcp.json` example

```json
{
  "mcpServers": {
    "speech-lab": {
      "command": "speech-lab-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "SPEECH_LAB_OUTPUT_DIR": "/absolute/path/to/speech-lab-mcp/data/out",
        "SPEECH_LAB_PIPER_URL": "http://127.0.0.1:8090",
        "SPEECH_LAB_POCKET_URL": "http://127.0.0.1:8091",
        "CARTESIA_API_KEY": "",
        "CARTESIA_VOICE_ID": ""
      }
    }
  }
}
```

On Windows, `command` can be the full path to `.venv\\Scripts\\speech-lab-mcp.exe`.

## Docker Compose

MCP only (Cartesia works if a key is set in the environment; local engines optional):

```bash
docker compose up --build mcp
```

Streamable HTTP endpoint: `http://127.0.0.1:8765/mcp`

Local Piper + Pocket:

```bash
docker compose --profile local up --build
```

Profiles:

| Profile | Services |
|---------|----------|
| *(default)* | `mcp` |
| `piper` | Piper TTS |
| `pocket` | Pocket TTS |
| `local` | Piper + Pocket |
| `woof` | Underdog Woof (set `WOOF_MODEL_DIR` in `.env`) |

Build contexts default to sibling checkouts:

- Piper → `../text-echo/tts`
- Pocket → `../../miso/pocket`
- Woof → `../agent-voice-tts/sidecars/woof-tts`

Override with `PIPER_BUILD_CONTEXT`, `POCKET_BUILD_CONTEXT`, `WOOF_BUILD_CONTEXT`.

WAVs are written to `./data/out` on the host.

## Transports

| Transport | Use |
|-----------|-----|
| `stdio` | Cursor / local agent subprocess |
| `streamable-http` | Compose / remote clients (`/mcp`) |
| `sse` | Legacy only — prefer streamable-http |

## Typical agent flow

1. `list_providers` / `provider_status` — confirm a healthy engine.
2. `list_voices` — pick a stable voice id per character.
3. `synthesize` — generate a WAV; copy the returned path into your project assets.
4. Keep a roster file in the consumer project so the same character always uses the same provider + voice.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Attribution

- **Author:** Stephen Phillips
- **Organization:** [HappyMonkeyAI](https://github.com/HappyMonkeyAI)
- **License:** MIT

Third-party engines remain under their own licenses (Piper voices, Pocket TTS, Underdog Woof non-commercial terms, Cartesia terms of service).
