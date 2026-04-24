from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


log = logging.getLogger("max.client")


class MaxApiError(RuntimeError):
    pass


class MaxClient:
    def __init__(self, token: str, *, base_url: str = "https://platform-api.max.ru", timeout_s: float = 10.0):
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": token},
            timeout=httpx.Timeout(timeout_s),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, MaxApiError)),
        wait=wait_exponential_jitter(initial=0.5, max=8.0),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _request(self, method: str, path: str, *, params: dict | None = None, json: Any | None = None) -> Any:
        try:
            r = await self._client.request(method, path, params=params, json=json)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise e

        if r.status_code in (429, 503):
            raise MaxApiError(f"MAX transient error {r.status_code}: {r.text}")
        if r.is_error:
            raise MaxApiError(f"MAX error {r.status_code}: {r.text}")
        if r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        return r.text

    async def me(self) -> dict:
        return await self._request("GET", "/me")

    async def send_message(
        self,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        text: str | None,
        attachments: list[dict] | None = None,
        format_: str | None = "markdown",
        notify: bool = True,
        disable_link_preview: bool | None = None,
    ) -> dict:
        if not user_id and not chat_id:
            raise ValueError("user_id or chat_id is required")
        params: dict[str, Any] = {}
        if user_id:
            params["user_id"] = user_id
        if chat_id:
            params["chat_id"] = chat_id
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview

        body: dict[str, Any] = {"text": text, "attachments": attachments, "notify": notify}
        if format_:
            body["format"] = format_
        return await self._request("POST", "/messages", params=params, json=body)

    async def answer_callback(
        self,
        *,
        callback_id: str,
        message: dict | None = None,
        notification: str | None = None,
    ) -> dict:
        # https://dev.max.ru/docs-api/methods/POST/answers
        body: dict[str, Any] = {}
        if message is not None:
            body["message"] = message
        if notification is not None:
            body["notification"] = notification
        return await self._request("POST", "/answers", params={"callback_id": callback_id}, json=body)

    async def create_subscription(self, *, url: str, update_types: list[str], secret: str | None = None) -> dict:
        # https://dev.max.ru/docs-api/methods/POST/subscriptions
        body: dict[str, Any] = {"url": url, "update_types": update_types}
        if secret:
            body["secret"] = secret
        return await self._request("POST", "/subscriptions", json=body)

    async def create_upload(self, *, type_: str) -> dict:
        # https://dev.max.ru/docs-api/methods/POST/uploads
        # type_: image|video|audio|file
        return await self._request("POST", "/uploads", params={"type": type_})

    async def upload_multipart_to_url(self, *, upload_url: str, file_path: str) -> dict:
        """
        Загружает файл по URL, который вернул POST /uploads.

        Важно: этот URL обычно НЕ на platform-api.max.ru, поэтому используем отдельный клиент.
        """
        async with httpx.AsyncClient(
            headers={"Authorization": self._token},
            timeout=httpx.Timeout(60.0),
        ) as c:
            with open(file_path, "rb") as f:
                r = await c.post(upload_url, files={"data": (file_path.split("/")[-1], f)})
        if r.is_error:
            raise MaxApiError(f"MAX upload error {r.status_code}: {r.text}")
        if r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        # На практике MAX upload endpoint возвращает JSON. Если нет — считаем ошибкой.
        raise MaxApiError(f"MAX upload returned non-JSON: {r.text[:2000]}")
