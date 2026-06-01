from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from jellyfin_music_replay.config import Config, PeriodConfig


@dataclass
class Period:
    period_type: str
    key: tuple[int, ...]
    name: str
    items: list[str]
    resolved_ids: list[str] = field(default_factory=list)


def _year_key(dt: datetime) -> tuple[int]:
    return (dt.year,)


def _half_key(dt: datetime) -> tuple[int, int]:
    return (dt.year, (dt.month - 1) // 6 + 1)


def _quarter_key(dt: datetime) -> tuple[int, int]:
    return (dt.year, (dt.month - 1) // 3 + 1)


def _format_period_name(
    period_type: str,
    key: tuple[int, ...],
    year_format: str,
    title_template: str,
) -> str:
    year_str = datetime(key[0], 1, 1).strftime(year_format)
    if period_type == "year":
        return title_template.format(year=year_str)
    elif period_type == "half":
        return title_template.format(year=year_str, half=key[1])
    elif period_type == "quarter":
        return title_template.format(year=year_str, quarter=key[1])


def _build_periods(
    playbacks: list[tuple[str, str, int]],
    period_type: str,
    key_fn,
    pc: PeriodConfig,
) -> list[Period]:
    if pc.disabled:
        return []

    # Aggregate: (period_key, item_name) -> total_duration
    totals: dict[tuple[tuple[int, ...], str], int] = defaultdict(int)
    for item_name, date_created_str, play_duration in playbacks:
        dt = datetime.fromisoformat(date_created_str)
        key = key_fn(dt)
        totals[(key, item_name)] += play_duration

    # Group by period_key
    by_period: dict[tuple[int, ...], list[tuple[str, int]]] = defaultdict(list)
    for (key, item_name), duration in totals.items():
        by_period[key].append((item_name, duration))

    # Sort each period's items by duration descending, apply limit
    periods = []
    for key in sorted(by_period.keys()):
        ranked = sorted(by_period[key], key=lambda x: x[1], reverse=True)[: pc.limit]
        name = _format_period_name(period_type, key, pc.year_format, pc.title_template)
        periods.append(Period(
            period_type=period_type,
            key=key,
            name=name,
            items=[item_name for item_name, _ in ranked],
        ))

    return periods


def aggregate_by_periods(
    playbacks: list[tuple[str, str, int]],
    config: Config,
) -> list[Period]:
    periods: list[Period] = []
    periods.extend(_build_periods(playbacks, "year", _year_key, config.year))
    periods.extend(_build_periods(playbacks, "half", _half_key, config.half))
    periods.extend(_build_periods(playbacks, "quarter", _quarter_key, config.quarter))
    return periods
