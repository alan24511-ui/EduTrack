"""Protocolo USB serie RC522: una línea ASCII `UID:<hexadecimal>\\n`."""

import re

_UID = re.compile(r"^UID:([0-9A-Fa-f]{8}|[0-9A-Fa-f]{14}|[0-9A-Fa-f]{20})$")


def parse_uid_line(line: str) -> str | None:
    """Retorna UID uppercase canónico; descarta líneas incompletas o inválidas."""
    match = _UID.fullmatch(line.strip())
    return match.group(1).upper() if match else None
