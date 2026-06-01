import sqlite3


def get_audio_playbacks(db_path: str) -> list[tuple[str, str, int]]:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT ItemName, DateCreated, PlayDuration "
            "FROM PlaybackActivity "
            "WHERE ItemType = 'Audio'"
        )
        return cursor.fetchall()
    finally:
        conn.close()
