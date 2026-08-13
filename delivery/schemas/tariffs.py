from decimal import Decimal
from typing import List, Any
from pydantic import BaseModel, Field
from enum import Enum


# Схема для CDEKAdapter.get_all_tariffs()

# Pydantic-схема для ответа

class ContragentType(str, Enum):
    LEGAL_ENTITY = "LEGAL_ENTITY"
    INDIVIDUAL = "INDIVIDUAL"


class TariffDeliveryModeSchema(BaseModel):
    delivery_mode: int
    delivery_mode_name: str
    tariff_code: int | None = None



class AdditionalOrderTypesSchema(BaseModel):
    without_additional_order_type: bool
    additional_order_types: list[Any] = Field(default_factory=list)


class AvailableTariffSchema(BaseModel):
    tariff_name: str

    weight_min: Decimal
    weight_max: Decimal
    weight_calc_max: Decimal

    length_min: int
    length_max: int

    width_min: int
    width_max: int

    height_min: int
    height_max: int

    order_types: list[Any] = Field(default_factory=list)

    payer_contragent_type: list[ContragentType] = Field(default_factory=list)
    sender_contragent_type: list[ContragentType] = Field(default_factory=list)
    recipient_contragent_type: list[ContragentType] = Field(default_factory=list)

    delivery_modes: list[TariffDeliveryModeSchema] = Field(default_factory=list)

    additional_order_types_param: AdditionalOrderTypesSchema | None = None


class AvailableTariffsResponseSchema(BaseModel):
    tariff_codes: List[AvailableTariffSchema]


# Схема для CDEKAdapter.pre_calculate_delivery()

# Pydantic-схема для ответа

class DeliveryDateRangeSchema(BaseModel):
    min: str
    max: str


class ServiceSchema(BaseModel):
    code: str
    sum: Decimal  # Изменено на Decimal для точного подсчета денег


class TariffResultSchema(BaseModel):
    delivery_sum: Decimal  # Изменено на Decimal
    period_min: int
    period_max: int
    delivery_date_range: DeliveryDateRangeSchema | None = None  # Современный синтаксис вместо Optional
    services: list[ServiceSchema] = Field(default_factory=list)  # Современный list и безопасный default_factory
    total_sum: Decimal  # Изменено на Decimal
    currency: str


class TariffItemSchema(BaseModel):
    tariff_code: str
    status: str
    result: TariffResultSchema


class TariffListResponseSchema(BaseModel):
    tariff_codes: list[TariffItemSchema] = Field(default_factory=list)
    errors: list[dict] | None = None  # Используются встроенные list и dict с оператором |
    warnings: list[dict] | None = None
