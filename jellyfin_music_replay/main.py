import sys

from jellyfin_music_replay.client import JellyfinClient
from jellyfin_music_replay.config import get_device_id, load_config
from jellyfin_music_replay.database import get_audio_playbacks
from jellyfin_music_replay.parser import parse_item_name
from jellyfin_music_replay.periods import aggregate_by_periods

MEDIA_BROWSER_CLIENT = "Jellyfin Music Replay"
VERSION = "0.1.0"


def main() -> None:
    config = load_config()
    device_id = get_device_id()

    # Read playback data
    playbacks = get_audio_playbacks(config.playback_reporting_db)
    print(f"Read {len(playbacks)} audio playback records from database")

    # Aggregate into periods
    periods = aggregate_by_periods(playbacks, config)
    print(f"Generated {len(periods)} period(s)")
    for p in periods:
        print(f"  {p.name}: {len(p.items)} items")

    if not periods:
        print("No periods to process. Exiting.")
        return

    # Authenticate with Jellyfin
    client = JellyfinClient(config.url)
    _, user_id = client.authenticate(
        config.username,
        config.password,
        MEDIA_BROWSER_CLIENT,
        config.device,
        device_id,
        VERSION,
    )
    print(f"Authenticated as user {user_id}")

    # Fetch all audio items and build lookup index
    audio_items = client.get_audio_items(user_id)
    print(f"Fetched {len(audio_items)} audio items from Jellyfin")

    jellyfin_index: dict[tuple[str, str, str], str] = {}
    for item in audio_items:
        key = (
            (item.get("Name") or "").strip(),
            (item.get("Album") or "").strip(),
            (item.get("AlbumArtist") or "").strip(),
        )
        jellyfin_index[key] = item["Id"]

    # Resolve ItemNames to IDs
    for period in periods:
        resolved_ids = []
        for item_name in period.items:
            parsed = parse_item_name(item_name)
            lookup_key = (parsed.name, parsed.album or "", parsed.album_artist)
            if lookup_key in jellyfin_index:
                resolved_ids.append(jellyfin_index[lookup_key])
            else:
                print(
                    f"WARNING: No match for '{item_name}' "
                    f"(Name='{parsed.name}', Album='{parsed.album}', AlbumArtist='{parsed.album_artist}')",
                    file=sys.stderr,
                )
        period.resolved_ids = resolved_ids

    # Fetch existing playlists
    existing_playlists = client.get_playlists(user_id)
    playlist_name_to_id = {p["Name"]: p["Id"] for p in existing_playlists}

    # Create or update playlists
    for period in periods:
        if not period.resolved_ids:
            print(f"Skipping '{period.name}' (no matched items)")
            continue

        body = {
            "Name": period.name,
            "Ids": period.resolved_ids,
            "UserId": user_id,
            "MediaType": "Audio",
            "Users": [],
            "IsPublic": config.is_public,
        }

        if period.name in playlist_name_to_id:
            client.update_playlist(playlist_name_to_id[period.name], body)
            print(f"Updated playlist: {period.name} ({len(period.resolved_ids)} items)")
        else:
            client.create_playlist(body)
            print(f"Created playlist: {period.name} ({len(period.resolved_ids)} items)")
