from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

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