from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, RootModel


# Запрос на создание подписки
class WebhookSubscriptionRequestSchema(BaseModel):
    type: Literal["ORDER_STATUS"]
    url: str


# Ошибка CDEK
class WebhookErrorSchema(BaseModel):
    code: str
    message: str


# Информация о запросе CDEK
class WebhookRequestInfoSchema(BaseModel):
    request_uuid: UUID
    type: Literal[
        "CREATE",
        "UPDATE",
        "DELETE",
        "AUTH",
        "GET",
    ]
    date_time: datetime
    state: Literal[
        "ACCEPTED",
        "SUCCESSFUL",
        "INVALID",
    ]
    errors: list[WebhookErrorSchema] = Field(
        default_factory=list
    )


# Информация о подписке
class WebhookSchema(BaseModel):
    uuid: UUID
    type: Literal[
        "ORDER_STATUS",
        "ORDER_MODIFIED",
        "PRINT_FORM",
        "RECEIPT",
        "DOWNLOAD_PHOTO",
        "PREALERT_CLOSED",
        "ACCOMPANYING_WAYBILL",
        "OFFICE_AVAILABILITY",
        "DELIV_PROBLEM",
        "DELIV_AGREEMENT",
        "COURIER_INFO",
    ]
    url: str


# Ответ создания / получения подписки
class WebhookSubscriptionResponseSchema(BaseModel):
    entity: WebhookSchema
    requests: list[WebhookRequestInfoSchema] = Field(
        default_factory=list
    )


# Ответ списка подписок
class WebhookSubscriptionsResponseSchema(
    RootModel[list[WebhookSchema]]
):
    pass


# Entity ответа удаления
class WebhookDeleteEntitySchema(BaseModel):
    uuid: UUID


# Ответ удаления подписки
class WebhookDeleteResponseSchema(BaseModel):
    entity: WebhookDeleteEntitySchema
    requests: list[WebhookRequestInfoSchema] = Field(
        default_factory=list
    )