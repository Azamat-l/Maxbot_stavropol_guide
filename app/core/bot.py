from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.actions import pack, unpack
from app.core.content import Attraction, ContentStore
from app.core.ui import btn_callback, btn_link, format_attraction_md, kb_inline, maps_link, share_deeplink
from app.db.repo import FavoritesRepo, UserRepo
from app.max.client import MaxClient
from app.max.schemas import Update, UpdateBotStarted, UpdateMessageCallback, UpdateMessageCreated


log = logging.getLogger("bot")


CATS = {
    "mineral_springs": "Родники и источники",
    "history_routes": "Исторические места",
    "views_cafes": "Достопримечательности",
    "seasonal": "Сезонные развлечения",
}


@dataclass
class Context:
    user_id: int
    chat_id: int | None
    callback_id: str | None = None
    user_locale: str | None = None


def _chunk_buttons(buttons: list[dict], per_row: int = 2) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for i in range(0, len(buttons), per_row):
        rows.append(buttons[i : i + per_row])
    return rows


def build_main_menu(store: ContentStore) -> tuple[str, list[dict]]:
    text = (
        "Привет! Я гид по **неочевидным** местам Ставропольского края.\n\n"
        "Выберите категорию или откройте фильтры/избранное."
    )
    cat_buttons = [btn_callback(title, pack("cat", {"c": cid})) for cid, title in CATS.items()]
    rows = _chunk_buttons(cat_buttons, per_row=1)
    rows.append([btn_callback("Фильтры", pack("filters", {})), btn_callback("Избранное", pack("fav_list", {}))])
    return text, [kb_inline(rows)]


def build_filters_menu(store: ContentStore, state: dict) -> tuple[str, list[dict]]:
    def v(key: str) -> str:
        return str(state.get(key) or "—")

    text = (
        "**Фильтры**\n"
        f"- Район: `{v('district')}`\n"
        f"- Сезон: `{v('season')}`\n"
        f"- Тип маршрута: `{v('route_type')}`\n\n"
        "Нажмите, чтобы выбрать/сбросить."
    )

    rows: list[list[dict]] = []
    rows.append([btn_callback("Выбрать район", pack("pick_district", {}))])
    rows.append([btn_callback("Выбрать сезон", pack("pick_season", {}))])
    rows.append([btn_callback("Выбрать тип", pack("pick_route", {}))])
    rows.append([btn_callback("Сбросить фильтры", pack("filters_reset", {}))])
    rows.append([btn_callback("Назад в меню", pack("menu", {}))])
    return text, [kb_inline(rows)]


def build_pick_list(title: str, items: list[str], action: str, back_action: str) -> tuple[str, list[dict]]:
    buttons = [btn_callback(x, pack(action, {"v": x})) for x in items]
    rows = _chunk_buttons(buttons, per_row=1)
    rows.append([btn_callback("← Назад", pack(back_action, {}))])
    return title, [kb_inline(rows)]


def build_attraction_card(a: Attraction, store: ContentStore, *, is_fav: bool) -> tuple[str, list[dict]]:
    text = format_attraction_md(a, store=store)
    rows: list[list[dict]] = []
    rows.append([btn_link("Открыть на карте", maps_link(a.lat, a.lon))])

    share_text = f"{a.title}\n{a.lat:.6f}, {a.lon:.6f}\n{a.description[:400]}"
    rows.append([btn_link("Поделиться", share_deeplink(share_text))])

    if is_fav:
        rows.append([btn_callback("★ Убрать из избранного", pack("fav_remove", {"id": a.id}))])
    else:
        rows.append([btn_callback("☆ В избранное", pack("fav_add", {"id": a.id}))])
    rows.append([btn_callback("← К списку", pack("list", {})), btn_callback("Меню", pack("menu", {}))])

    attachments = [kb_inline(rows)]
    if a.photo:
        # Вложения Max формируются как {type, payload}. Для image payload берётся из результата загрузки (см. POST /uploads).
        # Точную схему image payload нужно сверить в официальных объектах. [MAX_API_TODO]
        attachments.insert(0, a.photo)
    elif a.photo_link:
        # Фолбэк: ссылка на фото.
        rows.insert(0, [btn_link("Фото", a.photo_link)])

    return text, attachments


async def handle_update(
    update: Update,
    *,
    ctx: Context,
    api: MaxClient,
    store: ContentStore,
    user_repo: UserRepo,
    fav_repo: FavoritesRepo,
) -> None:
    await user_repo.upsert_user(ctx.user_id, locale=ctx.user_locale)

    if isinstance(update, UpdateMessageCreated):
        text_in = (update.message.body.text or "").strip() if update.message.body else ""
        if text_in.lower() in ("/start", "start", "меню", "menu"):
            await _send_menu(ctx, api, store)
            return
        if text_in.lower() in ("избранное", "/fav", "fav"):
            await _send_favorites(ctx, api, store, fav_repo)
            return
        if text_in.lower() in ("фильтры", "/filters", "filters"):
            state = await user_repo.get_state(ctx.user_id)
            await _send_filters(ctx, api, store, state)
            return

        # Неформальный ввод — показываем меню.
        await _send_menu(ctx, api, store)
        return

    if isinstance(update, UpdateBotStarted):
        # Запуск по диплинку `?start=` — можно использовать payload для автоперехода. [MAX_API_TODO]
        await _send_menu(ctx, api, store)
        return

    if isinstance(update, UpdateMessageCallback):
        act = unpack(update.callback.payload)
        ctx.callback_id = update.callback.callback_id
        if act is None:
            await api.answer_callback(callback_id=ctx.callback_id, notification="Не понял кнопку. Попробуйте ещё раз.")
            return

        await api.answer_callback(callback_id=ctx.callback_id, notification="Готово")
        await _handle_action(act.t, act.d, ctx, api, store, user_repo, fav_repo)
        return

    log.warning("Unknown update type: %s", getattr(update, "update_type", None))


async def _send_menu(ctx: Context, api: MaxClient, store: ContentStore) -> None:
    text, attachments = build_main_menu(store)
    await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=text, attachments=attachments, format_="markdown")


async def _send_filters(ctx: Context, api: MaxClient, store: ContentStore, state: dict) -> None:
    text, attachments = build_filters_menu(store, state)
    await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=text, attachments=attachments, format_="markdown")


async def _send_list(ctx: Context, api: MaxClient, store: ContentStore, state: dict) -> None:
    items = store.search(
        category=state.get("category"),
        district=state.get("district"),
        season=state.get("season"),
        route_type=state.get("route_type"),
        limit=10,
    )
    if not items:
        await api.send_message(
            user_id=ctx.user_id,
            chat_id=ctx.chat_id,
            text="По этим фильтрам ничего не нашёл. Откройте **Фильтры** и попробуйте иначе.",
            attachments=[kb_inline([[btn_callback("Фильтры", pack("filters", {})), btn_callback("Меню", pack("menu", {}))]])],
            format_="markdown",
        )
        return

    buttons = [btn_callback(a.title, pack("show", {"id": a.id})) for a in items]
    rows = _chunk_buttons(buttons, per_row=1)
    rows.append([btn_callback("Фильтры", pack("filters", {})), btn_callback("Меню", pack("menu", {}))])
    await api.send_message(
        user_id=ctx.user_id,
        chat_id=ctx.chat_id,
        text="Вот что подходит под ваш запрос. Выберите место:",
        attachments=[kb_inline(rows)],
        format_="markdown",
    )


async def _send_favorites(ctx: Context, api: MaxClient, store: ContentStore, fav_repo: FavoritesRepo) -> None:
    fav_ids = await fav_repo.list_ids(ctx.user_id)
    items = [store.get(i) for i in fav_ids]
    items = [a for a in items if a is not None]
    if not items:
        await api.send_message(
            user_id=ctx.user_id,
            chat_id=ctx.chat_id,
            text="Пока пусто. Откройте категории и добавьте места в избранное.",
            attachments=[kb_inline([[btn_callback("Меню", pack("menu", {}))]])],
            format_="markdown",
        )
        return
    buttons = [btn_callback(f"★ {a.title}", pack("show", {"id": a.id})) for a in items]
    rows = _chunk_buttons(buttons, per_row=1)
    rows.append([btn_callback("Меню", pack("menu", {}))])
    await api.send_message(
        user_id=ctx.user_id,
        chat_id=ctx.chat_id,
        text="**Избранное** — выберите место:",
        attachments=[kb_inline(rows)],
        format_="markdown",
    )


async def _handle_action(
    action: str,
    data: dict,
    ctx: Context,
    api: MaxClient,
    store: ContentStore,
    user_repo: UserRepo,
    fav_repo: FavoritesRepo,
) -> None:
    state = await user_repo.get_state(ctx.user_id)

    if action == "menu":
        await _send_menu(ctx, api, store)
        return

    if action == "filters":
        await _send_filters(ctx, api, store, state)
        return

    if action == "filters_reset":
        state.pop("district", None)
        state.pop("season", None)
        state.pop("route_type", None)
        await user_repo.set_state(ctx.user_id, state)
        await _send_filters(ctx, api, store, state)
        return

    if action == "pick_district":
        text, attachments = build_pick_list("Выберите район:", store.districts, "set_district", "filters")
        await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=text, attachments=attachments, format_="markdown")
        return

    if action == "pick_season":
        text, attachments = build_pick_list("Выберите сезон:", store.seasons, "set_season", "filters")
        await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=text, attachments=attachments, format_="markdown")
        return

    if action == "pick_route":
        text, attachments = build_pick_list("Выберите тип маршрута:", store.route_types, "set_route", "filters")
        await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=text, attachments=attachments, format_="markdown")
        return

    if action == "set_district":
        state["district"] = data.get("v")
        await user_repo.set_state(ctx.user_id, state)
        await _send_filters(ctx, api, store, state)
        return

    if action == "set_season":
        state["season"] = data.get("v")
        await user_repo.set_state(ctx.user_id, state)
        await _send_filters(ctx, api, store, state)
        return

    if action == "set_route":
        state["route_type"] = data.get("v")
        await user_repo.set_state(ctx.user_id, state)
        await _send_filters(ctx, api, store, state)
        return

    if action == "cat":
        state["category"] = data.get("c")
        await user_repo.set_state(ctx.user_id, state)
        await _send_list(ctx, api, store, state)
        return

    if action == "list":
        await _send_list(ctx, api, store, state)
        return

    if action == "show":
        a = store.get(str(data.get("id") or ""))
        if not a:
            await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text="Место не найдено.", attachments=None)
            return
        fav_ids = set(await fav_repo.list_ids(ctx.user_id))
        text, attachments = build_attraction_card(a, store, is_fav=(a.id in fav_ids))
        await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=text, attachments=attachments, format_="markdown")
        return

    if action == "fav_add":
        a_id = str(data.get("id") or "")
        ok = await fav_repo.add(ctx.user_id, a_id)
        msg = "Добавил в избранное." if ok else "Уже в избранном."
        await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=msg, attachments=None)
        return

    if action == "fav_remove":
        a_id = str(data.get("id") or "")
        ok = await fav_repo.remove(ctx.user_id, a_id)
        msg = "Убрал из избранного." if ok else "В избранном не было."
        await api.send_message(user_id=ctx.user_id, chat_id=ctx.chat_id, text=msg, attachments=None)
        return

    if action == "fav_list":
        await _send_favorites(ctx, api, store, fav_repo)
        return

    await api.send_message(
        user_id=ctx.user_id,
        chat_id=ctx.chat_id,
        text="Неизвестное действие. Откройте меню.",
        attachments=[kb_inline([[btn_callback("Меню", pack("menu", {}))]])],
        format_="markdown",
    )
