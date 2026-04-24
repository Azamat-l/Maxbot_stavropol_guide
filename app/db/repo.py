from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Favorite, User, UserState


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_user(self, user_id: int, locale: str | None = None) -> None:
        user = await self.session.get(User, user_id)
        if user is None:
            self.session.add(User(user_id=user_id, locale=locale))
            await self.session.commit()
            return
        if locale and user.locale != locale:
            user.locale = locale
            await self.session.commit()

    async def get_state(self, user_id: int) -> dict:
        st = await self.session.get(UserState, user_id)
        if st is None:
            return {}
        try:
            import json

            return json.loads(st.state_json or "{}")
        except Exception:
            return {}

    async def set_state(self, user_id: int, state: dict) -> None:
        import json

        st = await self.session.get(UserState, user_id)
        if st is None:
            self.session.add(UserState(user_id=user_id, state_json=json.dumps(state, ensure_ascii=False)))
            await self.session.commit()
            return
        st.state_json = json.dumps(state, ensure_ascii=False)
        await self.session.commit()


class FavoritesRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, attraction_id: str) -> bool:
        self.session.add(Favorite(user_id=user_id, attraction_id=attraction_id))
        try:
            await self.session.commit()
            return True
        except IntegrityError:
            await self.session.rollback()
            return False

    async def remove(self, user_id: int, attraction_id: str) -> bool:
        res = await self.session.execute(
            delete(Favorite).where(Favorite.user_id == user_id, Favorite.attraction_id == attraction_id)
        )
        await self.session.commit()
        return (res.rowcount or 0) > 0

    async def list_ids(self, user_id: int) -> list[str]:
        res = await self.session.execute(select(Favorite.attraction_id).where(Favorite.user_id == user_id))
        return [row[0] for row in res.all()]
