from datetime import date as date_type
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
from uuid import UUID



# Pydantic-схема для ответа от CDEKAdapter.get_order_uuid()

class CDEKOrderRequestErrorSchema(BaseModel):
    """Ошибка обработки запроса на заказ."""

    code: str | None = None
    message: str | None = None


class CDEKOrderRequestSchema1(BaseModel):
    """Информация о запросе CDEK."""

    request_uuid: str | None = None
    type: str | None = None
    date_time: str | None = None
    state: str | None = None
    errors: list[CDEKOrderRequestErrorSchema] = Field(
        default_factory=list,
    )


class CDEKOrderStatusSchema(BaseModel):
    """Статус заказа CDEK."""

    code: str
    name: str
    date_time: datetime
    city: str | None = None
    deleted: bool = False


class CDEKOrderEntitySchema(BaseModel):
    """Информация о заказе CDEK."""

    uuid: str

    type: int | None = None

    is_return: bool | None = None
    is_reverse: bool | None = None

    cdek_number: str | None = None
    number: str | None = None

    tariff_code: int | None = None
    comment: str | None = None

    shipment_point: str | None = None
    delivery_point: str | None = None

    items_cost_currency: str | None = None
    recipient_currency: str | None = None

    sender: dict | None = None
    seller: dict | None = None
    recipient: dict | None = None

    from_location: dict | None = None
    to_location: dict | None = None

    services: list[dict] = Field(
        default_factory=list,
    )

    packages: list[dict] = Field(
        default_factory=list,
    )

    statuses: list[CDEKOrderStatusSchema] = Field(
        default_factory=list,
    )

    is_client_return: bool | None = None
    delivery_mode: str | None = None
    has_reverse_order: bool | None = None

    delivery_detail: dict | None = None

    calls: dict = Field(
        default_factory=dict,
    )


class CDEKOrderResponseSchema(BaseModel):
    """Ответ CDEK при получении заказа по UUID."""

    entity: CDEKOrderEntitySchema

    requests: list[CDEKOrderRequestSchema1] = Field(
        default_factory=list,
    )

    related_entities: list[dict] = Field(
        default_factory=list,
    )


# Pydantic-схема для ответа от CDEKAdapter.post_order()

class CDEKOrderCreateRequestSchema(BaseModel):
    """Информация о запросе на регистрацию заказа."""

    request_uuid: str
    type: str
    date_time: str
    state: str
    errors: list[CDEKOrderRequestErrorSchema] = Field(
        default_factory=list,
    )


class CDEKOrderCreateResponseSchema(BaseModel):
    """Ответ CDEK на регистрацию заказа."""

    entity: dict
    requests: list[CDEKOrderCreateRequestSchema] = Field(
        default_factory=list,
    )
    related_entities: list[dict] = Field(
        default_factory=list,
    )


# Pydantic-схема для ответа от CDEKAdapter.cancel_delivery()

class CdekOrderErrorSchema(BaseModel):
    code: str | None = None
    additional_code: str | None = None
    message: str | None = None


class CdekOrderWarningSchema(BaseModel):
    code: str | None = None
    message: str | None = None


class CdekOrderRequestSchema(BaseModel):
    request_uuid: UUID | None = None
    type: Literal[
        "CREATE",
        "UPDATE",
        "DELETE",
        "AUTH",
        "GET",
        "CREATE_CLIENT_RETURN",
    ] | None = None
    date_time: datetime | None = None
    state: Literal[
        "ACCEPTED",
        "WAITING",
        "SUCCESSFUL",
        "INVALID",
    ] | None = None
    errors: list[CdekOrderErrorSchema] = Field(
        default_factory=list
    )
    warnings: list[CdekOrderWarningSchema] = Field(
        default_factory=list
    )


class CdekOrderEntitySchema(BaseModel):
    uuid: UUID | None = None


class CdekRelatedEntitySchema(BaseModel):
    uuid: UUID | None = None

    type: Literal[
        "return_order",
        "direct_order",
        "client_return_order",
        "client_direct_order",
        "waybill",
        "barcode",
        "reverse_order",
        "delivery",
    ]

    url: str | None = None
    create_time: datetime | None = None
    cdek_number: str | None = None
    date: date_type | None = None
    time_from: str | None = None
    time_to: str | None = None


class CdekDeleteOrderResponseSchema(BaseModel):
    entity: CdekOrderEntitySchema
    requests: list[CdekOrderRequestSchema] = Field(
        default_factory=list
    )
    related_entities: list[CdekRelatedEntitySchema] = Field(
        default_factory=list
    )