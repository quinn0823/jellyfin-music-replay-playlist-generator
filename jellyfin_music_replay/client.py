import requests


def _build_auth_header(
    client: str, device: str, device_id: str, version: str, token: str | None = None
) -> str:
    parts = [
        f'MediaBrowser Client="{client}"',
        f'Device="{device}"',
        f'DeviceId="{device_id}"',
        f'Version="{version}"',
    ]
    if token:
        parts.append(f'Token="{token}"')
    return ", ".join(parts)


class JellyfinClient:
    def __init__(self, url: str) -> None:
        self._url = url.rstrip("/")
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"
        self._session.headers["Content-Type"] = "application/json"

    def authenticate(
        self,
        username: str,
        password: str,
        client_name: str,
        device: str,
        device_id: str,
        version: str,
    ) -> tuple[str, str]:
        self._session.headers["Authorization"] = _build_auth_header(
            client_name, device, device_id, version
        )
        resp = self._session.post(
            f"{self._url}/Users/AuthenticateByName",
            json={"Username": username, "Pw": password},
        )
        resp.raise_for_status()
        data = resp.json()

        access_token = data["AccessToken"]
        user_id = data["User"]["Id"]

        self._session.headers["Authorization"] = _build_auth_header(
            client_name, device, device_id, version, access_token
        )
        return access_token, user_id

    def get_audio_items(self, user_id: str) -> list[dict]:
        resp = self._session.get(
            f"{self._url}/Items",
            params={"userId": user_id, "recursive": "true", "includeItemTypes": "Audio"},
        )
        resp.raise_for_status()
        return resp.json().get("Items", [])

    def get_playlists(self, user_id: str) -> list[dict]:
        resp = self._session.get(
            f"{self._url}/Items",
            params={"userId": user_id, "recursive": "true", "includeItemTypes": "Playlist"},
        )
        resp.raise_for_status()
        return resp.json().get("Items", [])

    def create_playlist(self, body: dict) -> str:
        resp = self._session.post(f"{self._url}/Playlists", json=body)
        resp.raise_for_status()
        return resp.json()["Id"]

    def update_playlist(self, playlist_id: str, body: dict) -> None:
        resp = self._session.post(f"{self._url}/Playlists/{playlist_id}", json=body)
        resp.raise_for_status()
