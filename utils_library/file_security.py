import io
import json
from typing import BinaryIO, Literal, Tuple

import magic
from fastapi import HTTPException, status

# Жёсткие лимиты
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_NOTES = 1000
MAX_RECORDS = 1000

# Разрешённые типы → логический формат
ALLOWED_MIME: dict[str, Literal["csv", "json"]] = {
    "text/csv": "csv",
    "application/json": "json",
    # некоторые браузеры шлют csv как text/plain — разрешим осторожно:
    "text/plain": "csv",
}

SNIFF_LEN = 4096  # сколько байт читаем для magic


def _sniff_mime(first_bytes: bytes) -> str:
    # определяем по содержимому, а не по названию файла
    # magic.from_buffer вернёт, например, 'text/csv' или 'application/json'
    return magic.from_buffer(first_bytes, mime=True)


def _resolve_format(
    content_type: str | None, magic_mime: str
) -> Literal["csv", "json"]:
    # по magic
    if magic_mime in ALLOWED_MIME:
        return ALLOWED_MIME[magic_mime]

    # fallback по заголовку (бывает полезно из-за нестандартных boundary)
    if content_type and content_type in ALLOWED_MIME:
        return ALLOWED_MIME[content_type]

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Unsupported file type: {magic_mime}",
    )


def stream_into_memory(fileobj: BinaryIO) -> Tuple[io.BytesIO, bytes]:
    buf = io.BytesIO()
    total = 0
    first_chunk = b""

    while True:
        chunk = fileobj.read(64 * 1024)  # читаем кусками
        if not chunk:
            break
        if not first_chunk:
            first_chunk = chunk[:SNIFF_LEN]
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large (>{MAX_FILE_SIZE} bytes)",
            )
        buf.write(chunk)

    buf.seek(0)
    return buf, first_chunk or b""


def validate_and_prepare(
    fileobj: BinaryIO,
    content_type: str | None,
) -> Tuple[io.BytesIO, Literal["csv", "json"]]:
    mem, first = stream_into_memory(fileobj)
    magic_mime = _sniff_mime(first)
    fmt = _resolve_format(content_type, magic_mime)
    return mem, fmt


def parse_json_array(mem: io.BytesIO) -> list[dict]:
    try:
        data = json.load(mem)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of objects")
    if len(data) > MAX_NOTES:
        raise HTTPException(status_code=400, detail=f"Too many items (> {MAX_NOTES})")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"Item #{i} is not an object")
    mem.seek(0)
    return data
