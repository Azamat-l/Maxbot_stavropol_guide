from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


class MaxBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class User(MaxBaseModel):
    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    username: str | None = None


class Recipient(MaxBaseModel):
    # В документации Recipient может быть пользователем или чатом. Поля зависят от контекста. [MAX_API_TODO]
    user_id: int | None = None
    chat_id: int | None = None


class MessageBody(MaxBaseModel):
    text: str | None = None
    attachments: list[dict[str, Any]] | None = None


class Message(MaxBaseModel):
    sender: User | None = None
    recipient: Recipient | None = None
    timestamp: int | None = None
    body: MessageBody | None = None
    url: str | None = None


class Callback(MaxBaseModel):
    callback_id: str = Field(..., description="Идентификатор callback для POST /answers")
    payload: str | None = None
    user: User | None = None
    chat_id: int | None = None


class UpdateMessageCreated(MaxBaseModel):
    update_type: Literal["message_created"]
    timestamp: int
    message: Message
    user_locale: str | None = None


class UpdateBotStarted(MaxBaseModel):
    update_type: Literal["bot_started"]
    timestamp: int
    chat_id: int
    user: User
    payload: str | None = None


class UpdateMessageCallback(MaxBaseModel):
    # Структура описана косвенно (types включает message_callback, callback_id берётся из updates[i].callback.callback_id).
    # Полную схему следует сверить в docs-api/objects/Update наследниках. [MAX_API_TODO]
    update_type: Literal["message_callback"]
    timestamp: int | None = None
    callback: Callback


Update = UpdateMessageCreated | UpdateBotStarted | UpdateMessageCallback
