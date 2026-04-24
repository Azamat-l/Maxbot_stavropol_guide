from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.config import settings
from app.max.client import MaxClient


"""
Загрузка локальных изображений в MAX и запись attachment payload в data/attractions.json.

Как работает:
- В attractions.json у места должен быть ключ:
  - photo_local: "data/photos/my.jpg"   (путь на файловой системе сервера/контейнера, где запускаешь скрипт)
- Скрипт делает:
  1) POST https://platform-api.max.ru/uploads?type=image  -> { "url": "...", ... }
  2) POST {url} multipart/form-data  data=@file          -> JSON payload (для image)
  3) Записывает в объект места:
     photo: { "type": "image", "payload": <payload_json> }

После этого бот начнёт отправлять фото прямо в чат (как вложение).

[MAX_API_TODO] Если MAX изменит формат payload для image, нужно использовать фактический JSON ответа upload.
"""


DATA_PATH = Path("data/attractions.json")


async def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit("data/attractions.json not found")

    doc = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    attractions: list[dict] = list(doc.get("attractions") or [])

    client = MaxClient(settings.max_bot_token)
    try:
        updated = 0
        skipped = 0

        for a in attractions:
            local_path = a.get("photo_local")
            if not local_path:
                skipped += 1
                continue
            if a.get("photo"):
                skipped += 1
                continue

            p = Path(str(local_path))
            if not p.exists():
                raise SystemExit(f"photo_local file not found: {p}")

            up = await client.create_upload(type_="image")
            upload_url = up.get("url")
            if not upload_url:
                raise SystemExit(f"Bad /uploads response (no url): {up}")

            payload = await client.upload_multipart_to_url(upload_url=upload_url, file_path=str(p))

            a["photo"] = {"type": "image", "payload": payload}
            updated += 1
            print(f"Uploaded image for {a.get('id')} -> ok")

        DATA_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Done. updated={updated}, skipped={skipped}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())

