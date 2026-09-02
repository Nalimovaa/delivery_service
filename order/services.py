from delivery.enums import CDEKDeliveryMode
from delivery.models import OrderDelivery, CdekDelivery
from delivery.schemas.tariffs import ShopCalculateDeliveryResultDTO
from delivery.services.locations import CDEKLocationValidationService, CDEKDeliveryPointService
from rest_framework.exceptions import ValidationError


class CDEKOrderService:
    """ Сервис формирования данных доставки CDEK для созданного OrderDelivery.
    Режим доставки определяется выбранным тарифом и приходит в shop_result.
    Пользователь не передает delivery_mode повторно.
    В зависимости от режима определяется,
    какие данные нужны со стороны магазина и покупателя:
    - адрес;
    - ПВЗ;
    - постамат.
    """

    # Откуда забирается отправление.
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

    # Куда доставляется отправление.
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
        delivery_data: dict[int, dict],
    ) -> CdekDelivery:
        """
        "delivery_data": {
        "1": {
            "address_to": "ул. Стара Загора, д. 130",
            "postal_code_to": "443114"
        },
        "4": {
            "delivery_point": "SAM12"
        }
    }
        """

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
        """ Заполняет данные отправителя.
        Данные магазина полностью берутся из Shop.
        Для режима "от двери":
        - город;
        - регион;
        - район;
        - страна;
        - адрес;
        - индекс.
        Для режима "от ПВЗ/склада/постамата":
        - код пункта отправления.
        """
        if delivery_mode in self.DOOR_FROM_MODES:
            # Полностью валидируем данные магазина.
            self.location_validator.validate(
                location=shop.location_from,
                location_region=shop.location_from_region,
                location_district=shop.location_from_district,
                location_country=shop.location_from_country,
                postal_code=shop.postal_code,
                delivery_point=None
            )
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
            cdek_delivery.address_from = shop.address
            cdek_delivery.postal_code_from = shop.postal_code

            return

        if delivery_mode in (
                self.WAREHOUSE_FROM_MODES
                | self.POSTAMAT_FROM_MODES
        ):
            self.location_validator.validate(
                location=None,
                location_region=None,
                location_district=None,
                location_country=None,
                postal_code=None,
                delivery_point=shop.delivery_point
            )
            cdek_delivery.shipment_point = shop.delivery_point

            return

        raise ValidationError(
            f"Неподдерживаемый режим доставки CDEK: "
            f"{delivery_mode}"
        )

    def _fill_to(
            self,
            *,
            cdek_delivery: CdekDelivery,
            delivery_mode: int,
            delivery_data: dict,
    ):
        """ Заполняет данные получателя.
        Для доставки до двери:
        - город;
        - регион;
        - район;
        - страна берутся из User;
        - адрес и почтовый индекс берутся из delivery_data.
        Для доставки в ПВЗ/постамат:
        - код ПВЗ берется из delivery_data;
        - город и адрес определяются по самому ПВЗ. """

        # Получение до двери
        if delivery_mode in self.DOOR_TO_MODES:
            postal_code = delivery_data.get("postal_code_to")
            address = delivery_data.get("address_to")

            if not postal_code:
                raise ValidationError(
                    {
                        "postal_code_to": (
                            "Почтовый индекс обязателен "
                            "для доставки до двери."
                        )
                    }
                )

            if not address:
                raise ValidationError(
                    {
                        "address_to": (
                            "Адрес обязателен "
                            "для доставки до двери."
                        )
                    }
                )

            # Валидируем город пользователя + переданный индекс.
            self.location_validator.validate(
                location=self.user.location_to,
                location_region=self.user.location_to_region,
                location_district=self.user.location_to_district,
                location_country=self.user.location_to_country,
                postal_code=delivery_data.get("postal_code_to"),
                delivery_point=None
            )

            # Город и регион берем из User.
            cdek_delivery.location_to = self.user.location_to
            cdek_delivery.location_to_region = self.user.location_to_region
            cdek_delivery.location_to_district = self.user.location_to_district
            cdek_delivery.location_to_country = self.user.location_to_country
            # Адрес и индекс пользователь указал непосредственно для этого заказа.
            cdek_delivery.address_to = (
                delivery_data.get("address_to")
            )
            cdek_delivery.postal_code_to = (
                delivery_data.get("postal_code_to")
            )

            return

        # Получение в ПВЗ / на склад
        if delivery_mode in (
                self.WAREHOUSE_TO_MODES
                | self.POSTAMAT_TO_MODES
        ):
            delivery_point = delivery_data.get("delivery_point")

            if not delivery_point:
                raise ValidationError(
                    {
                        "delivery_point": (
                            "Необходимо выбрать " "пункт получения CDEK."
                        )
                    }
                )
            self.location_validator.validate(
                location=None,
                location_region=None,
                location_district=None,
                location_country=None,
                postal_code=None,
                delivery_point= delivery_data.get("delivery_point")
            )

            cdek_delivery.delivery_point = (
                delivery_data.get("delivery_point")
            )
            return
