from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Attraction:
    id: str
    title: str
    category: str
    district: str
    route_type: str | None
    seasons: list[str]
    difficulty: str
    lat: float
    lon: float
    description: str
    best_time: str
    safety_tips: str
    photo: dict | None  # { "type": "...", "payload": {...} } — как в AttachmentRequest [MAX_API_TODO]
    photo_link: str | None


class ContentStore:
    def __init__(self, json_path: Path):
        self.json_path = json_path
        self._attractions: dict[str, Attraction] = {}
        self._categories: dict[str, str] = {}
        self._districts: list[str] = []
        self._seasons: list[str] = []
        self._route_types: list[str] = []

    def reload(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        self._categories = dict(data.get("categories", {}))
        items = []
        for raw in data.get("attractions", []):
            items.append(
                Attraction(
                    id=str(raw["id"]),
                    title=str(raw["title"]),
                    category=str(raw["category"]),
                    district=str(raw["district"]),
                    route_type=(str(raw["route_type"]) if raw.get("route_type") else None),
                    seasons=[str(x) for x in (raw.get("seasons") or [])],
                    difficulty=str(raw.get("difficulty") or "unknown"),
                    lat=float(raw["gps"]["lat"]),
                    lon=float(raw["gps"]["lon"]),
                    description=str(raw.get("description") or ""),
                    best_time=str(raw.get("best_time") or ""),
                    safety_tips=str(raw.get("safety_tips") or ""),
                    photo=(raw.get("photo") if isinstance(raw.get("photo"), dict) else None),
                    photo_link=(str(raw["photo_link"]) if raw.get("photo_link") else None),
                )
            )

        self._attractions = {a.id: a for a in items}
        self._districts = sorted({a.district for a in items})
        self._seasons = sorted({s for a in items for s in a.seasons})
        self._route_types = sorted({a.route_type for a in items if a.route_type})

    @property
    def categories(self) -> dict[str, str]:
        return self._categories

    @property
    def districts(self) -> list[str]:
        return self._districts

    @property
    def seasons(self) -> list[str]:
        return self._seasons

    @property
    def route_types(self) -> list[str]:
        return self._route_types

    def get(self, attraction_id: str) -> Attraction | None:
        return self._attractions.get(attraction_id)

    def search(
        self,
        *,
        category: str | None,
        district: str | None,
        season: str | None,
        route_type: str | None,
        limit: int = 10,
    ) -> list[Attraction]:
        res = []
        for a in self._attractions.values():
            if category and a.category != category:
                continue
            if district and a.district != district:
                continue
            if season and season not in a.seasons:
                continue
            if route_type and (a.route_type or "") != route_type:
                continue
            res.append(a)
        res.sort(key=lambda x: x.title)
        return res[: max(1, int(limit))]
