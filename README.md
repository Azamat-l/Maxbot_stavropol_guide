## Max бот‑гид по неочевидным местам Ставропольского края

### Что это
Production‑шаблон чат‑бота для мессенджера **Max** (Bot API `platform-api.max.ru`) в режиме **Webhook**:
- категории / фильтры / карточки мест
- избранное (SQLite/Postgres)
- callback‑кнопки (через `POST /answers`)
- контент в `data/attractions.json` с горячей перезагрузкой

### Быстрый старт (локально)
1) Установите Python 3.11+
2) Установите зависимости:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3) Настройте переменные окружения:

```bash
copy .env.example .env
```

4) Запустите:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Проверка:
- `GET /healthz`

### Webhook в Max
См. `app/admin/register_webhook.py` — скрипт создаёт подписку через `POST https://platform-api.max.ru/subscriptions`.

### Контент
Файл `data/attractions.json`. Можно обновлять и перезагружать:
- CLI: `python -m app.admin.reload_content`
- HTTP: `POST /admin/reload-content` (заголовок `X-Admin-Key`)

### Фото прямо в чат (как вложение image)
1) Положите картинки на сервер в папку `data/photos/` и пропишите у места поле `photo_local`, например:
`"photo_local": "data/photos/beryozovaya.jpg"`
2) Загрузите картинки в MAX и запишите `photo` payload в JSON:

```bash
python -m app.admin.upload_images
```

После этого бот будет отправлять фото **внутри сообщения** (вложение `image`).

### Docker
См. `Dockerfile` и `docker-compose.yml`.
