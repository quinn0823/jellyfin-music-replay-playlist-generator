# Jellyfin Music Replay

Generate music replay playlists for Jellyfin, based on the [Playback Reporting](https://github.com/jellyfin/jellyfin-plugin-playbackreporting) plugin.

The tool reads your playback history from the Playback Reporting SQLite database, ranks songs by total play duration for each year / half-year / quarter, then creates or updates the corresponding playlists in Jellyfin.

## Prerequisites

- **[Jellyfin Server](https://jellyfin.org/)**: tested with `10.10.7`
- **[Playback Reporting](https://github.com/jellyfin/jellyfin-plugin-playbackreporting) plugin**: tested with `16.0.0.0`
- **[Python](https://www.python.org/)**: tested with `3.14`
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip

## Quick Start

### uv

```bash
# Clone the repo
git clone https://github.com/quinn0823/jellyfin-music-replay.git

cd jellyfin-music-replay

# Install dependencies
uv sync

# Configure
cp .env.example .env
# Edit .env with your Jellyfin server URL, credentials, and database path
```

```bash
# Run
uv run -m jellyfin_music_replay
```

Or use the installed script:

```bash
uv run jellyfin-music-replay
```

### pip

```bash
# Clone the repo
git clone https://github.com/quinn0823/jellyfin-music-replay.git

cd jellyfin-music-replay

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Jellyfin Server URL, credentials, and database path
```

```bash
# Run
python -m jellyfin_music_replay
```

## Configuration

All settings are controlled via environment variables or a `.env` file in the project root.

### Required

| Variable                | Description                         | Example                                                     |
| ----------------------- | ----------------------------------- | ----------------------------------------------------------- |
| `URL`                   | Jellyfin Server URL                 | `http://localhost:8096`                                     |
| `USERNAME`              | Jellyfin username                   |
| `PASSWORD`              | Jellyfin password                   |
| `PLAYBACK_REPORTING_DB` | Path to the `playback_reporting.db` | `C:\ProgramData\Jellyfin\Server\data\playback_reporting.db` |

### Optional

| Variable    | Default  | Description                                         |
| ----------- | -------- | --------------------------------------------------- |
| `DEVICE`    | `Python` | Device name shown in the Jellyfin dashboard         |
| `IS_PUBLIC` | `false`  | Whether generated playlists are publicly accessible |

### Playlist Controls

Each period type (year, half-year, quarter) can be independently enabled/disabled and customized:

| Variable                        | Default                    | Description                         |
| ------------------------------- | -------------------------- | ----------------------------------- |
| `IS_YEAR_REPLAY_DISABLED`       | `false`                    | Disable year replay generation      |
| `YEAR_REPLAY_LIMIT`             | `100`                      | Max songs per year replay           |
| `YEAR_REPLAY_YEAR_FORMAT`       | `%Y`                       | Year format (`strftime`)            |
| `YEAR_REPLAY_TITLE_TEMPLATE`    | `Replay {year}`            | Playlist name template              |
| `IS_HALF_REPLAY_DISABLED`       | `false`                    | Disable half-year replay generation |
| `HALF_REPLAY_LIMIT`             | `50`                       | Max songs per half-year replay      |
| `HALF_REPLAY_YEAR_FORMAT`       | `%Y`                       | Year format (`strftime`)            |
| `HALF_REPLAY_TITLE_TEMPLATE`    | `Replay {year} H{half}`    | Playlist name template              |
| `IS_QUARTER_REPLAY_DISABLED`    | `false`                    | Disable quarter replay generation   |
| `QUARTER_REPLAY_LIMIT`          | `25`                       | Max songs per quarter replay        |
| `QUARTER_REPLAY_YEAR_FORMAT`    | `%Y`                       | Year format (`strftime`)            |
| `QUARTER_REPLAY_TITLE_TEMPLATE` | `Replay {year} Q{quarter}` | Playlist name template              |

#### Template Placeholders

- `{year}`: formatted according to the corresponding `*_YEAR_FORMAT`
- `{half}`: `1` (Jan–Jun) or `2` (Jul–Dec)
- `{quarter}`: `1` (Jan–Mar), `2` (Apr–Jun), `3` (Jul–Sep), `4` (Oct–Dec)

#### Examples

| Config                                                                    | Resulting Playlist Names                          |
| ------------------------------------------------------------------------- | ------------------------------------------------- |
| Defaults                                                                  | `Replay 2025`, `Replay 2025 H1`, `Replay 2025 Q1` |
| `HALF_REPLAY_TITLE_TEMPLATE='Replay {year}H{half}'`                       | `Replay 25H1`, `Replay 25H2`                      |
| `YEAR_REPLAY_YEAR_FORMAT='%y'`, `YEAR_REPLAY_TITLE_TEMPLATE='Top {year}'` | `Top 25`, `Top 26`                                |

## How It Works

1. **Read playback data** — Queries the `PlaybackActivity` table from the Playback Reporting SQLite database, filtering for `Audio` items only.
2. **Aggregate by period** — Splits records into year / half-year / quarter buckets, then ranks songs by **total play duration** (not play count) within each period.
3. **Authenticate** — Logs in to Jellyfin with your username and password (API key auth cannot manage playlists).
4. **Resolve tracks** — Parses each song's `ItemName` (format: `{AlbumArtist} - {Name} ({Album})`) and matches it against your Jellyfin library to get the item IDs.
5. **Create or update playlists** — For each period with results, either creates a new playlist or updates an existing one (matched by name).

Any songs that can't be matched to your Jellyfin library are skipped with a warning on the console.

## Copyright

Licensed under the GNU General Public License v3.0.

Copyright (c) 2026 Jonathan Chiu
