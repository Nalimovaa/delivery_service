from django.db import transaction

from delivery.enums import CDEKDeliveryMode
from delivery.models import OrderDelivery, CdekDelivery
from delivery.schemas.tariffs import ShopCalculateDeliveryResultDTO
from delivery.services.locations import CDEKLocationValidationService, CDEKDeliveryPointService
from rest_framework.exceptions import ValidationError


class CDEKOrderService:

    DOOR_FROM_MODES = {
        CDEKDeliveryMode.DOOR_TO_DOOR,
        CDEKDeliveryMode.DOOR_TO_WAREHOUSE,
        CDEKDeliveryMode.DOOR_TO_POSTAMAT,
    }

    WAREHOUSE_FROM_MODES = {
        CDEKDeliveryMode.WAREHOUSE_TO_DOOR,
        CDEKDeliveryMode.WAREHOUSE_TO_WAREHOUSE,
        CDEKDeliveryMode.WAREHOUSE_TO_POSTAMAT,
    }

    POSTAMAT_FROM_MODES = {
        CDEKDeliveryMode.POSTAMAT_TO_DOOR,
        CDEKDeliveryMode.POSTAMAT_TO_WAREHOUSE,
        CDEKDeliveryMode.POSTAMAT_TO_POSTAMAT,
    }

    DOOR_TO_MODES = {
        CDEKDeliveryMode.DOOR_TO_DOOR,
        CDEKDeliveryMode.WAREHOUSE_TO_DOOR,
        CDEKDeliveryMode.POSTAMAT_TO_DOOR,
    }

    WAREHOUSE_TO_MODES = {
        CDEKDeliveryMode.DOOR_TO_WAREHOUSE,
        CDEKDeliveryMode.WAREHOUSE_TO_WAREHOUSE,
        CDEKDeliveryMode.POSTAMAT_TO_WAREHOUSE,
    }

    POSTAMAT_TO_MODES = {
        CDEKDeliveryMode.DOOR_TO_POSTAMAT,
        CDEKDeliveryMode.WAREHOUSE_TO_POSTAMAT,
        CDEKDeliveryMode.POSTAMAT_TO_POSTAMAT,
    }

    def __init__(self, user):
        self.user = user
        self.location_validator = CDEKLocationValidationService()
        self.delivery_point_service = CDEKDeliveryPointService()

    def _create_cdek_delivery(
        self,
        *,
        order_delivery: OrderDelivery,
        shop_result: ShopCalculateDeliveryResultDTO,
        delivery_data: dict,
    ) -> CdekDelivery:

        if shop_result.tariff_code is None:
            raise ValidationError(
                "Для заказа CDEK не выбран тариф."
            )

        if shop_result.delivery_mode is None:
            raise ValidationError(
                "Для выбранного тарифа CDEK "
                "не определен режим доставки."
            )

        delivery_mode = shop_result.delivery_mode

        cdek_delivery = CdekDelivery.objects.create(
            order_delivery=order_delivery,
            tariff_code=shop_result.tariff_code,
            delivery_mode=delivery_mode,
            delivery_mode_name=shop_result.delivery_mode_name,
            preliminary_price=shop_result.delivery_sum,
        )

        self._fill_from(
            cdek_delivery=cdek_delivery,
            delivery_mode=delivery_mode,
            shop=order_delivery.shop,
        )

        self._fill_to(
            cdek_delivery=cdek_delivery,
            delivery_mode=delivery_mode,
            delivery_data=delivery_data,
        )

        cdek_delivery.save()

        return cdek_delivery

    def _fill_from(
            self,
            *,
            cdek_delivery: CdekDelivery,
            delivery_mode: int,
            shop,
    ):
        if delivery_mode in self.DOOR_FROM_MODES:
            cdek_delivery.location_from = shop.location_from
            cdek_delivery.location_from_region = (
                shop.location_from_region
            )
            cdek_delivery.location_from_district = (
                shop.location_from_district
            )
            cdek_delivery.location_from_country = (
                shop.location_from_country
            )
            cdek_delivery.address_from = shop.address_from
            cdek_delivery.postal_code_from = shop.postal_code

            return

        if delivery_mode in self.WAREHOUSE_FROM_MODES:
            # Здесь должен быть код ПВЗ/склада отправления,
            # если он хранится у магазина.
            cdek_delivery.shipment_point = shop.shipment_point

            return

        if delivery_mode in self.POSTAMAT_FROM_MODES:
            # Здесь аналогично нужен выбранный
            # постамат отправления.
            cdek_delivery.shipment_point = shop.shipment_point

            return

        raise ValidationError(
            f"Неподдерживаемый режим доставки CDEK: "
            f"{delivery_mode}"
        )

    def _fill_to(
            self,
            *,
            cdek_delivery,
            delivery_mode,
            delivery_data,
    ):
        if delivery_mode in self.DOOR_TO_MODES:
            self.location_validator.validate(
                location=delivery_data["location_to"],
                location_region=delivery_data["location_to_region"],
                location_district=delivery_data.get(
                    "location_to_district"
                ),
                location_country=delivery_data[
                    "location_to_country"
                ],
                postal_code=delivery_data.get(
                    "postal_code_to"
                ),
            )

            cdek_delivery.location_to = (
                delivery_data["location_to"]
            )
            cdek_delivery.location_to_region = (
                delivery_data["location_to_region"]
            )
            cdek_delivery.location_to_district = (
                delivery_data.get("location_to_district")
            )
            cdek_delivery.location_to_country = (
                delivery_data["location_to_country"]
            )
            cdek_delivery.address_to = (
                delivery_data["address_to"]
            )
            cdek_delivery.postal_code_to = (
                delivery_data.get("postal_code_to")
            )

            return

        if delivery_mode in self.WAREHOUSE_TO_MODES:
            self._set_delivery_point(
                cdek_delivery=cdek_delivery,
                delivery_data=delivery_data,
            )
            return

        if delivery_mode in self.POSTAMAT_TO_MODES:
            self._set_delivery_point(
                cdek_delivery=cdek_delivery,
                delivery_data=delivery_data,
            )
            return

    def _validate_door_delivery_data(
            self,
            delivery_data: dict,
    ):
        required_fields = (
            "location_to",
            "location_to_region",
            "location_to_country",
            "address_to",
        )

        missing = [
            field
            for field in required_fields
            if not delivery_data.get(field)
        ]

        if missing:
            raise ValidationError(
                {
                    field: "Поле обязательно для доставки до двери."
                    for field in missing
                }
            )

        if delivery_data.get("delivery_point"):
            raise ValidationError(
                "Для доставки до двери нельзя указывать "
                "delivery_point."
            )

    def _set_delivery_point(
            self,
            *,
            cdek_delivery,
            delivery_data,
    ):
        delivery_point = delivery_data.get(
            "delivery_point"
        )

        if not delivery_point:
            raise ValidationError(
                {
                    "delivery_point": (
                        "Необходимо выбрать пункт "
                        "доставки CDEK."
                    )
                }
            )

        point = (
            self.delivery_point_service
            .get_delivery_point(delivery_point)
        )

        if point is None:
            raise ValidationError(
                {
                    "delivery_point": (
                        "Выбранный пункт CDEK не найден "
                        "или недоступен."
                    )
                }
            )

        cdek_delivery.delivery_point = delivery_point

    def _validate_delivery_point_data(
            self,
            delivery_data: dict,
    ):
        if not delivery_data.get("delivery_point"):
            raise ValidationError(
                {
                    "delivery_point": (
                        "Необходимо выбрать пункт доставки CDEK."
                    )
                }
            )

        address_fields = (
            "location_to",
            "location_to_region",
            "location_to_district",
            "location_to_country",
            "address_to",
            "postal_code_to",
        )

        if any(
                delivery_data.get(field)
                for field in address_fields
        ):
            raise ValidationError(
                "Для доставки в пункт CDEK нельзя указывать "
                "адрес доставки."
            )


