from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.bot import Context, handle_update
from app.core.content import ContentStore
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimiter
from app.db.engine import SessionLocal, engine
from app.db.repo import FavoritesRepo, UserRepo
from app.db.startup import init_db
from app.max.client import MaxClient, MaxApiError
from app.max.schemas import Update


configure_logging(settings.log_level)
log = logging.getLogger("app")

app = FastAPI(title="Max Attractions Bot", version="1.0.0")

update_adapter = TypeAdapter(Update)
rate_limiter = RateLimiter(settings.rate_limit_per_minute)

content = ContentStore(Path("data/attractions.json"))


async def get_db() -> AsyncSession:
    async with SessionLocal() as s:
        yield s


@app.on_event("startup")
async def _startup() -> None:
    content.reload()
    await init_db(engine)
    app.state.max = MaxClient(settings.max_bot_token)
    log.info("Startup completed")


@app.on_event("shutdown")
async def _shutdown() -> None:
    maxc: MaxClient = app.state.max
    await maxc.aclose()


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/admin/reload-content")
async def admin_reload_content(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> dict:
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="unauthorized")
    content.reload()
    return {"ok": True}


@app.post(settings.webhook_path)
async def webhook_max(
    request: Request,
    response: Response,
    x_max_bot_api_secret: str | None = Header(default=None, alias="X-Max-Bot-Api-Secret"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1) Rate limit (защита от флуда/DoS).
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"ip:{ip}"):
        raise HTTPException(status_code=429, detail="rate_limited")

    # 2) Валидация, что webhook пришёл от MAX (если secret задан при POST /subscriptions).
    if settings.max_webhook_secret:
        if x_max_bot_api_secret != settings.max_webhook_secret:
            raise HTTPException(status_code=401, detail="bad_secret")

    payload: Any = await request.json()

    # 3) Разбор Update по официальным схемам/наследникам.
    try:
        update = update_adapter.validate_python(payload)
    except ValidationError:
        # MAX может добавлять новые типы/поля. Не падаем, но логируем. [MAX_API_TODO]
        log.warning("Unknown update payload: %s", payload)
        return {"ok": True}

    # 4) Достаём user_id/chat_id максимально безопасно (структуры отличаются для DM/чатов). [MAX_API_TODO]
    user_id: int | None = None
    chat_id: int | None = None
    user_locale: str | None = None

    if getattr(update, "update_type", None) == "message_created":
        try:
            user_id = update.message.sender.user_id if update.message.sender else None
            user_locale = getattr(update, "user_locale", None)
            chat_id = update.message.recipient.chat_id if update.message.recipient else None
        except Exception:
            pass
    elif getattr(update, "update_type", None) == "bot_started":
        user_id = update.user.user_id
        chat_id = update.chat_id
    elif getattr(update, "update_type", None) == "message_callback":
        user_id = update.callback.user.user_id if update.callback.user else None
        chat_id = update.callback.chat_id

    if user_id is None:
        log.warning("No user_id in update: %s", payload)
        return {"ok": True}

    # 5) Бизнес‑логика.
    api: MaxClient = app.state.max
    user_repo = UserRepo(db)
    fav_repo = FavoritesRepo(db)

    ctx = Context(user_id=user_id, chat_id=chat_id, user_locale=user_locale)
    try:
        await handle_update(update, ctx=ctx, api=api, store=content, user_repo=user_repo, fav_repo=fav_repo)
    except MaxApiError as e:
        log.exception("Max API error: %s", e)
    except Exception as e:
        log.exception("Unhandled error: %s", e)

    # MAX ожидает HTTP 200 <= 30s.
    return {"ok": True}
