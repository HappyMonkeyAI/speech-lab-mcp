from __future__ import annotations

import argparse

from speech_lab_mcp.config import load_settings
from speech_lab_mcp.server import run_server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="SpeechLab MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default=None,
        help="Override SPEECH_LAB_TRANSPORT",
    )
    parser.add_argument("--host", default=None, help="HTTP bind host")
    parser.add_argument("--port", type=int, default=None, help="HTTP bind port")
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.transport:
        settings.transport = args.transport
    if args.host:
        settings.host = args.host
    if args.port is not None:
        settings.port = args.port
    run_server(settings)


if __name__ == "__main__":
    main()
