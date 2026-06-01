from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedItemName:
    album_artist: str
    name: str
    album: str | None


def parse_item_name(item_name: str) -> ParsedItemName:
    parts = item_name.rsplit(" - ", 1)
    if len(parts) != 2:
        return ParsedItemName(album_artist=item_name.strip(), name=item_name.strip(), album=None)

    album_artist = parts[0].strip()
    name_album = parts[1]

    if name_album.endswith(")") and "(" in name_album:
        depth = 0
        open_pos = -1
        for i in range(len(name_album) - 1, -1, -1):
            if name_album[i] == ")":
                depth += 1
            elif name_album[i] == "(":
                depth -= 1
                if depth == 0:
                    open_pos = i
                    break

        if open_pos >= 0:
            album = name_album[open_pos + 1 : -1].strip()
            name = name_album[:open_pos].strip()
            return ParsedItemName(album_artist=album_artist, name=name, album=album)

    return ParsedItemName(album_artist=album_artist, name=name_album.strip(), album=None)
