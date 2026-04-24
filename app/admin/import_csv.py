from __future__ import annotations

import csv
import json
from pathlib import Path


"""
Импорт CSV -> data/attractions.json (упрощённо).

CSV колонки (пример):
id,title,category,district,route_type,seasons,difficulty,lat,lon,description,best_time,safety_tips,photo_link

- seasons: через ;
- lat/lon: float

Фото через вложение (upload token/payload) сюда не подтягиваем — это отдельный шаг. [MAX_API_TODO]
"""


def main() -> None:
    src = Path("data/attractions.csv")
    dst = Path("data/attractions.json")
    if not src.exists():
        raise SystemExit("No data/attractions.csv found")

    attractions = []
    with src.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            attractions.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "category": row["category"],
                    "district": row["district"],
                    "route_type": row.get("route_type") or None,
                    "seasons": [x.strip() for x in (row.get("seasons") or "").split(";") if x.strip()],
                    "difficulty": row.get("difficulty") or "unknown",
                    "gps": {"lat": float(row["lat"]), "lon": float(row["lon"])},
                    "description": row.get("description") or "",
                    "best_time": row.get("best_time") or "",
                    "safety_tips": row.get("safety_tips") or "",
                    "photo_link": row.get("photo_link") or None,
                }
            )

    # Категории можно вести вручную (человекочитаемые названия).
    doc = {
        "categories": {},
        "attractions": attractions,
    }
    dst.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written {dst} with {len(attractions)} attractions")


if __name__ == "__main__":
    main()
