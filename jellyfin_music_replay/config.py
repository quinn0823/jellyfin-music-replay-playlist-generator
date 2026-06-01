import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class PeriodConfig:
    disabled: bool
    limit: int
    year_format: str
    title_template: str


@dataclass(frozen=True)
class Config:
    device: str
    url: str
    username: str
    password: str
    playback_reporting_db: str
    is_public: bool
    year: PeriodConfig
    half: PeriodConfig
    quarter: PeriodConfig


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, "").strip() or default


def _env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key, "").strip().lower()
    if not value:
        return default
    return value in ("true", "1", "yes")


def _env_int(key: str, default: int = 0) -> int:
    value = os.environ.get(key, "").strip()
    if not value:
        return default
    return int(value)


def _load_period_config(prefix: str, limit_default: int, template_default: str) -> PeriodConfig:
    return PeriodConfig(
        disabled=_env_bool(f"IS_{prefix}_REPLAY_DISABLED"),
        limit=_env_int(f"{prefix}_REPLAY_LIMIT", limit_default),
        year_format=_env(f"{prefix}_REPLAY_YEAR_FORMAT", "%Y"),
        title_template=_env(f"{prefix}_REPLAY_TITLE_TEMPLATE", template_default),
    )


def get_device_id() -> str:
    device_id_path = Path(".device_id")
    if device_id_path.exists() and device_id_path.read_text().strip():
        return device_id_path.read_text().strip()
    new_id = uuid.uuid4().hex
    device_id_path.write_text(new_id)
    return new_id


def load_config() -> Config:
    load_dotenv()

    return Config(
        device=_env("DEVICE", "Python"),
        url=_env("URL"),
        username=_env("USERNAME"),
        password=_env("PASSWORD"),
        playback_reporting_db=_env("PLAYBACK_REPORTING_DB"),
        is_public=_env_bool("IS_PUBLIC"),
        year=_load_period_config("YEAR", 100, "Replay {year}"),
        half=_load_period_config("HALF", 50, "Replay {year} H{half}"),
        quarter=_load_period_config("QUARTER", 25, "Replay {year} Q{quarter}"),
    )
