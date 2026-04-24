from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    t: str
    d: dict


def pack(action: str, data: dict) -> str:
    """
    Callback payload в Max — строка.
    Кладём JSON, чтобы безопасно расширять протокол.
    """
    return json.dumps({"a": action, "d": data}, ensure_ascii=False, separators=(",", ":"))


def unpack(payload: str | None) -> Action | None:
    if not payload:
        return None
    try:
        obj = json.loads(payload)
        if isinstance(obj, dict) and isinstance(obj.get("a"), str) and isinstance(obj.get("d"), dict):
            return Action(t=obj["a"], d=obj["d"])
    except Exception:
        return None
    return None
