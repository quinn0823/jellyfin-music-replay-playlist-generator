# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jellyfin Music Replay — 从 Jellyfin 播放统计生成音乐回忆播放列表（类似 Spotify Wrapped / Apple Music Replay）。
Reads playback history from a SQLite database (Playback Reporting plugin), ranks songs by total play duration per period (year/half/quarter), then creates/updates playlists in Jellyfin via its REST API.

The full specification and workflow details are in `README_CLAUDE.md` (Chinese). Read that file first for any implementation work.

## Development Commands

```bash
# Install dependencies (uv)
uv sync
```

## Architecture

### Data Flow

```
SQLite DB (PlaybackActivity table)
  -> Parse ItemName into (AlbumArtist, Name, Album)
  -> Match against Jellyfin Audio items via API
  -> Generate ranked playlists per period
  -> Create/update playlists in Jellyfin via API
```

### Key Design Decisions

- **ItemName, not ItemId**: Songs are matched by `ItemName` from the playback DB (format: `{AlbumArtist} - {Name} ({Album})`), parsed to extract three fields, then matched against Jellyfin's `Name`, `Album`, and `AlbumArtist` fields to find the correct `Id`.
- **Rightmost `()` pair is the Album**: ItemName parsing treats the rightmost matched pair of parentheses as the album name, everything after ` - ` and before that album as the track name, and everything before ` - ` as the album artist.
- **Play duration, not play count**: Ranking is by total `PlayDuration` (seconds), not number of plays.
- **Username/password auth** (not API key): API key-based auth can't update/delete playlists, so the app authenticates by username/password to obtain an access token.

### API Auth Headers

All Jellyfin API requests need:
```
Authorization: MediaBrowser Client="{MEDIA_BROWSER_CLIENT}", Device="{DEVICE}", DeviceId="{device_id}", Version="{VERSION}", Token="{access_token}"
```

### Environment Variables

See `.env.example` and `README_CLAUDE.md` for the full list. Key required vars:
- `URL` — Jellyfin server URL
- `USERNAME`, `PASSWORD` — Jellyfin credentials
- `PLAYBACK_REPORTING_DB` — path to playback_reporting.db SQLite file

Optional vars control period enable/disable, title templates, and year formatting per period type.

### Local State

- `.device_id` — random UUID stored in a text file at the project root (generated once, reused for subsequent runs)

### Project Structure (Planned)

```
samples/                      # Sample API responses for reference
specification/                # Jellyfin OpenAPI spec

README_CLAUDE.md              # Full specification (read this first)
.env.example                  # Environment variable template
pyproject.toml                # Project config (uv)
```

## Key Notes

- `README_CLAUDE.md` is the authoritative specification — always read it before implementing
- The Jellyfin OpenAPI spec at `specification/jellyfin-openapi-10.10.7.json` is the API reference
- `samples/` contains real API response samples referenced by the spec
- User-facing output (playlist names, UI text) must be in English despite the spec being in Chinese
