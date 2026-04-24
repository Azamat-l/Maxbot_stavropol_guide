from __future__ import annotations

import asyncio

from app.config import settings
from app.max.client import MaxClient


async def main() -> None:
    if not settings.public_base_url:
        raise SystemExit("PUBLIC_BASE_URL is required (e.g. https://your-domain.com)")

    url = settings.public_base_url.rstrip("/") + settings.webhook_path
    client = MaxClient(settings.max_bot_token)
    try:
        res = await client.create_subscription(
            url=url,
            update_types=[
                "message_created",
                "message_callback",
                "bot_started",
            ],
            secret=settings.max_webhook_secret,
        )
        print(res)
        print(f"Webhook url registered: {url}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
