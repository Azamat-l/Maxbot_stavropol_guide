from __future__ import annotations

from pathlib import Path

from app.core.content import ContentStore


def main() -> None:
    store = ContentStore(Path("data/attractions.json"))
    store.reload()
    print(f"OK. Loaded: {len(store.search(category=None, district=None, season=None, route_type=None, limit=10_000))} items")


if __name__ == "__main__":
    main()
