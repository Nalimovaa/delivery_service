from delivery.adapters.cdek import CDEKAdapter
from delivery.enums import CDEKDeliveryMode
from delivery.exceptions import CDEKBusinessError
from delivery.models import OrderDelivery, CdekDelivery
from delivery.schemas.tariffs import ShopCalculateDeliveryResultDTO
from delivery.services.locations import CDEKLocationValidationService, CDEKDeliveryPointService, CDEKCityService
from rest_framework.exceptions import ValidationError
import uuid


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
        self.adapter = CDEKAdapter()
        self.location_validator = CDEKLocationValidationService()
        self.city_service = CDEKCityService()
        self.delivery_point_service = CDEKDeliveryPointService()

    def _create_cdek_delivery(
        self,
        *,
        order_delivery: OrderDelivery,
        shop_result: ShopCalculateDeliveryResultDTO,
        delivery_data: dict,
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

    def _generate_cdek_order_data(
            self,
            *,
            cdek_delivery: CdekDelivery,
    ) -> dict:
        """
        Формирует payload для регистрации заказа CDEK.

        Все необходимые данные получает через CdekDelivery:
        CdekDelivery -> OrderDelivery -> Order / Shop / OrderProduct.
        """

        order_delivery = cdek_delivery.order_delivery
        order = order_delivery.order
        shop = order_delivery.shop
        user = order.owner

        delivery_mode = CDEKDeliveryMode(
            cdek_delivery.delivery_mode
        )

        # Товары конкретного отправления.
        order_items = list(
            order_delivery.items.select_related(
                "unique_product",
            )
        )

        items = [
            self.adapter.generate_order_item(
                ware_key=str(order_item.unique_product_id),
                name=order_item.product_name,
                cost=order_item.price,
                amount=order_item.amount,
                weight=order_item.unique_product.weight,
            )
            for order_item in order_items
        ]

        total_weight = sum(
            order_item.unique_product.weight * order_item.amount
            for order_item in order_items
        )

        packages = [
            self.adapter.generate_order_package(
                number=cdek_delivery.pk,
                weight=total_weight,
                items=items,
            )
        ]

        sender = self.adapter.generate_order_sender(
            company=shop.name,
            name=shop.name,
            contragent_type="LEGAL_ENTITY",
            phone=shop.phone_number,
        )

        recipient = self.adapter.generate_order_recipient(
            name=user.fullname,
            phone=user.phone_number,
        )

        from_location = None
        shipment_point = None

        if delivery_mode in self.DOOR_FROM_MODES:
            city_from = self.city_service.get_city(
                city=cdek_delivery.location_from,
                region=cdek_delivery.location_from_region,
                sub_region=cdek_delivery.location_from_district,
                country=cdek_delivery.location_from_country,
            )

            if city_from is None:
                raise ValidationError(
                    "Населенный пункт отправления не найден "
                    "в справочнике CDEK."
                )

            from_location = self.adapter.generate_from_location(
                code=city_from.code,
                country_code=cdek_delivery.location_from_country,
                region_code=city_from.region_code,
                address=cdek_delivery.address_from,
                postal_code=cdek_delivery.postal_code_from,
            )
        else:
            shipment_point = cdek_delivery.shipment_point

        to_location = None
        delivery_point = None

        if delivery_mode in self.DOOR_TO_MODES:
            city_to = self.city_service.get_city(
                city=cdek_delivery.location_to,
                region=cdek_delivery.location_to_region,
                sub_region=cdek_delivery.location_to_district,
                country=cdek_delivery.location_to_country,
            )

            if city_to is None:
                raise ValidationError(
                    "Населенный пункт получения не найден "
                    "в справочнике CDEK."
                )

            to_location = self.adapter.generate_to_location(
                code=city_to.code,
                country_code=cdek_delivery.location_to_country,
                region_code=city_to.region_code,
                address=cdek_delivery.address_to,
                postal_code=cdek_delivery.postal_code_to,
            )
        else:
            delivery_point = cdek_delivery.delivery_point

        return self.adapter.generate_data_order(
            number=f"{order.pk}-{order_delivery.pk}-{uuid.uuid4().hex[:8]}",
            comment=f"Заказ #{order.pk}",
            tariff_code=cdek_delivery.tariff_code,
            delivery_mode=delivery_mode,
            sender=sender,
            recipient=recipient,
            packages=packages,
            services=[],
            shipment_point=shipment_point,
            delivery_point=delivery_point,
            from_location=from_location,
            to_location=to_location,
        )

    def create_delivery(
            self,
            *,
            order_delivery: OrderDelivery,
            shop_result: ShopCalculateDeliveryResultDTO,
            delivery_data: dict,
    ) -> CdekDelivery:

        # 1. Создаём локальную CdekDelivery.
        cdek_delivery = self._create_cdek_delivery(
            order_delivery=order_delivery,
            shop_result=shop_result,
            delivery_data=delivery_data,
        )

        # 2. Формируем payload для CDEK.
        data = self._generate_cdek_order_data(
            cdek_delivery=cdek_delivery,
        )

        # 3. Регистрируем заказ в CDEK.
        response = self.adapter.create_delivery(
            data=data,
        )

        # 4. Получаем UUID заказа CDEK.
        entity = response.entity

        cdek_uuid = entity.get("uuid")

        if not cdek_uuid:
            raise CDEKBusinessError(
                operation="post_order",
                message="CDEK не вернул UUID созданного заказа.",
                response_data=response.model_dump(),
            )

        # 5. Сохраняем UUID.
        cdek_delivery.cdek_uuid = cdek_uuid
        cdek_delivery.save(
            update_fields=["cdek_uuid"]
        )

        # 6. Получаем заказ из CDEK по UUID.
        order_response = self.adapter.get_order_uuid(
            uuid=cdek_uuid,
        )

        statuses = order_response.entity.statuses

        if statuses:
            latest_status = statuses[-1]

            cdek_delivery.order_status = latest_status.code
            cdek_delivery.save(update_fields=["order_status"])

        return cdek_delivery
