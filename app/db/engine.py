from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def make_engine() -> AsyncEngine:
    # SQLite не создаёт промежуточные папки для файла БД.
    # По умолчанию у нас sqlite+aiosqlite:///./var/app.db -> создаём ./var заранее.
    url = make_url(settings.database_url)
    if url.drivername.startswith("sqlite") and url.database:
        try:
            db_path = Path(url.database)
            # Для относительных путей приводим к workspace‑относительному виду (как задано в DATABASE_URL).
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Не блокируем старт из‑за mkdir (напр. in-memory sqlite). [MAX_API_TODO]
            pass

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


engine = make_engine()
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
