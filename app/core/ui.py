from __future__ import annotations

import urllib.parse

from app.core.content import Attraction, ContentStore


def kb_inline(button_rows: list[list[dict]]) -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": button_rows,
        },
    }


def btn_callback(text: str, payload: str) -> dict:
    return {"type": "callback", "text": text, "payload": payload}


def btn_link(text: str, url: str) -> dict:
    return {"type": "link", "text": text, "url": url}


def share_deeplink(text: str) -> str:
    # Документация: диплинк `:share` — подставляет текст в поле отправки.
    # https://dev.max.ru/help/deeplinks
    return f"https://max.ru/:share?text={urllib.parse.quote(text, safe='')}"


def maps_link(lat: float, lon: float) -> str:
    # Яндекс.Карты (веб). Формат: pt=lon,lat (метка), z=масштаб, l=слой карты.
    # Док: https://yandex.ru/dev/yandex-apps-launch-maps/doc/ru/
    return f"https://yandex.ru/maps/?pt={lon:.6f},{lat:.6f}&z=17&l=map"


def format_attraction_md(a: Attraction, *, store: ContentStore) -> str:
    cat_name = store.categories.get(a.category, a.category)
    lines = [
        f"**{a.title}**",
        f"_Категория_: {cat_name}",
        f"_Район_: {a.district}",
        f"_Сложность_: {a.difficulty}",
        f"_Лучшее время_: {a.best_time}",
        f"_Сезоны_: {', '.join(a.seasons) if a.seasons else '—'}",
        "",
        a.description.strip(),
        "",
        f"**GPS**: `{a.lat:.6f}, {a.lon:.6f}`",
        "",
        f"**Безопасность**: {a.safety_tips.strip()}",
    ]
    return "\n".join([x for x in lines if x is not None])
