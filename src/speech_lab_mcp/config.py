from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    transport: Literal["stdio", "streamable-http", "sse"] = Field(
        default="stdio",
        validation_alias="SPEECH_LAB_TRANSPORT",
    )
    host: str = Field(default="127.0.0.1", validation_alias="SPEECH_LAB_HOST")
    port: int = Field(default=8765, validation_alias="SPEECH_LAB_PORT")
    output_dir: Path = Field(
        default=Path("./data/out"),
        validation_alias="SPEECH_LAB_OUTPUT_DIR",
    )

    piper_url: str | None = Field(default=None, validation_alias="SPEECH_LAB_PIPER_URL")
    pocket_url: str | None = Field(default=None, validation_alias="SPEECH_LAB_POCKET_URL")
    woof_url: str | None = Field(default=None, validation_alias="SPEECH_LAB_WOOF_URL")

    http_timeout_s: float = Field(default=60.0, validation_alias="SPEECH_LAB_HTTP_TIMEOUT_S")
    max_wav_bytes: int = Field(default=50 * 1024 * 1024, validation_alias="SPEECH_LAB_MAX_WAV_BYTES")

    cartesia_api_key: str | None = Field(default=None, validation_alias="CARTESIA_API_KEY")
    cartesia_voice_id: str | None = Field(default=None, validation_alias="CARTESIA_VOICE_ID")
    cartesia_model_id: str = Field(default="sonic-3.5", validation_alias="CARTESIA_MODEL_ID")
    cartesia_sample_rate: int = Field(default=24000, validation_alias="CARTESIA_SAMPLE_RATE")

    default_provider: str | None = Field(
        default=None,
        validation_alias="SPEECH_LAB_DEFAULT_PROVIDER",
    )
    default_voice: str | None = Field(
        default=None,
        validation_alias="SPEECH_LAB_DEFAULT_VOICE",
    )

    @field_validator(
        "piper_url",
        "pocket_url",
        "woof_url",
        "cartesia_api_key",
        "cartesia_voice_id",
        "default_provider",
        "default_voice",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def ensure_output_dir(self) -> Path:
        path = self.output_dir.expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


def load_settings() -> Settings:
    return Settings()
