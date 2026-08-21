from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


# Pydantic-схема для ответа от CDEKAdapter.get_cities()

class CDEKCitiesSchema(BaseModel):
    """Населенный пункт из справочника СДЭК."""

    code: int
    city_uuid: UUID
    city: str

    fias_guid: UUID | None = None

    country_code: str
    country: str

    region: str
    region_code: int | None = None

    sub_region: str | None = None

    longitude: float | None = None
    latitude: float | None = None

    time_zone: str | None = None

    payment_limit: Decimal


class CDEKCitiesErrorSchema(BaseModel):
    """Ошибка API СДЭК."""

    code: str
    message: str


class CDEKCitiesErrorResponseSchema(BaseModel):
    """Ответ API СДЭК с ошибками."""

    errors: list[CDEKCitiesErrorSchema]


# Pydantic-схема для ответа от CDEKAdapter.get_delivery_points()

class CDEKDeliveryPointPhoneSchema(BaseModel):
    number: str


class CDEKDeliveryPointImageSchema(BaseModel):
    url: str


class CDEKDeliveryPointWorkTimeSchema(BaseModel):
    day: int
    time: str


class CDEKDeliveryPointLocationSchema(BaseModel):
    country_code: str
    region_code: int
    region: str
    city_code: int
    city: str
    postal_code: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    address: str | None = None
    address_full: str | None = None
    city_uuid: UUID


class CDEKDeliveryPointSchema(BaseModel):
    """Пункт выдачи/приема CDEK."""

    code: str
    name: str
    uuid: UUID

    address_comment: str | None = None
    nearest_station: str | None = None
    nearest_metro_station: str | None = None

    work_time: str | None = None

    phones: list[CDEKDeliveryPointPhoneSchema] = Field(
        default_factory=list
    )

    email: str | None = None
    note: str | None = None

    type: str
    owner_code: str

    take_only: bool
    is_handout: bool
    is_reception: bool
    is_dressing_room: bool
    is_ltl: bool

    have_cashless: bool
    have_cash: bool
    have_fast_payment_system: bool
    allowed_cod: bool

    office_image_list: list[CDEKDeliveryPointImageSchema] = Field(
        default_factory=list
    )

    work_time_list: list[CDEKDeliveryPointWorkTimeSchema] = Field(
        default_factory=list
    )

    work_time_exception_list: list[dict] = Field(
        default_factory=list
    )

    status: str

    location: CDEKDeliveryPointLocationSchema

    ltl_acceptance_partners: bool
    ltl_issuance_partners: bool
    fulfillment: bool


class CDEKDeliveryPointsErrorSchema(BaseModel):
    """Ошибка API CDEK."""

    code: str
    message: str


class CDEKDeliveryPointsErrorResponseSchema(BaseModel):
    """Ответ API CDEK с ошибками."""

    errors: list[CDEKDeliveryPointsErrorSchema]