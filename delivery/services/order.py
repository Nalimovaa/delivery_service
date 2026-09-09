from delivery.adapters.cdek import CDEKAdapter
from delivery.enums import StockReservationStatus
from delivery.models import CdekDelivery, CdekDeliveryStatusHistory, CdekRequestLog, OrderDelivery
from delivery.schemas.order import CDEKOrderResponseSchema, CDEKOrderCreateResponseSchema
from django.db import transaction
from decimal import Decimal
from delivery.status_mappers.cdek_mapper import CdekDeliveryStatusMapper
from order.enams import OrderDeliveryStatus
from order.models import OrderProduct
from order.services import OrderStatusService
from product.services import CartService, StockService
from delivery.enums import CDEKDeliveryMode
from delivery.exceptions import CDEKBusinessError
from delivery.kafka.producers import KafkaProducer
from delivery.kafka.schemas import CDEKOrderAcceptedEvent
from delivery.kafka.topics import KafkaTopic
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

        self.request_log_service = CdekRequestLogService()
        self.status_service = CdekOrderStatusService()

        self.kafka_producer = KafkaProducer()

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

    def _check_create_response(
            self,
            response: CDEKOrderCreateResponseSchema,
    ):
        invalid_requests = [
            request
            for request in response.requests
            if request.state == "INVALID"
        ]

        if not invalid_requests:
            return

        request = invalid_requests[0]

        raise CDEKBusinessError(
            operation="post_order",
            code=None,
            message="CDEK не смог зарегистрировать заказ.",
            response_data=response.model_dump(),
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

        # 4. Сохраняем результат запроса CREATE.
        self.request_log_service.save_create_response(
            cdek_delivery=cdek_delivery,
            response=response,
        )

        # 5. Проверяем результат бизнес-операции.
        self._check_create_response(
            response=response,
        )

        # 6. Получаем UUID заказа CDEK.
        cdek_uuid = response.entity.get("uuid")

        if not cdek_uuid:
            raise CDEKBusinessError(
                operation="post_order",
                message="CDEK не вернул UUID созданного заказа.",
                response_data=response.model_dump(),
            )

        # 7. Сохраняем UUID.
        cdek_delivery.cdek_uuid = cdek_uuid
        cdek_delivery.save(
            update_fields=["cdek_uuid"],
        )

        # 8. Первый GET заказа по UUID.
        #    На этом этапе cdek_number может отсутствовать —
        #    это нормально, заказ ещё может регистрироваться.
        response = self.adapter.get_order_uuid(
            uuid=cdek_uuid,
        )

        # 9. Логируем первый ответ GET.
        self.request_log_service.save_order_response(
            cdek_delivery=cdek_delivery,
            response=response,
        )

        # 10. Сохраняем актуальные статусы заказа.
        self.status_service.save_statuses(
            cdek_delivery=cdek_delivery,
            response=response,
        )

        # 11. Передаём событие дальше.
        event = CDEKOrderAcceptedEvent(
            cdek_delivery_id=cdek_delivery.id,
            cdek_uuid=cdek_uuid,
        )
        KafkaProducer().send(
            topic=KafkaTopic.CDEK_ORDER_ACCEPTED,
            message=event.model_dump(),
        )

        return cdek_delivery


class CdekOrderStatusService:

    def save_statuses(
        self,
        *,
        cdek_delivery: CdekDelivery,
        response: CDEKOrderResponseSchema,
    ):
        statuses = response.entity.statuses

        if not statuses:
            return

        for status in statuses:
            CdekDeliveryStatusHistory.objects.get_or_create(
                cdek_delivery=cdek_delivery,
                status_code=status.code,
                status_date=status.date_time,
                defaults={
                    "status_name": status.name,
                    "city": status.city,
                    "is_deleted": status.deleted,
                },
            )

        latest_status = max(
            statuses,
            key=lambda status: status.date_time,
        )

        cdek_delivery.order_status = latest_status.code
        cdek_delivery.save(
            update_fields=["order_status"]
        )


class CdekRequestLogService:

    def _save_request(
        self,
        *,
        cdek_delivery: CdekDelivery,
        cdek_uuid: str | None,
        request_type: str | None,
        state: str | None,
        date_time,
        errors: list | None = None,
        response_data: dict | None = None,
    ):
        errors = errors or []

        first_error = errors[0] if errors else None

        CdekRequestLog.objects.create(
            cdek_delivery=cdek_delivery,
            cdek_uuid=cdek_uuid,
            request_type=request_type,
            state=state,
            date_time=date_time,
            error_code=(
                first_error.code
                if first_error
                else None
            ),
            error_message=(
                first_error.message
                if first_error
                else None
            ),
            response_data=response_data or {},
        )

    def save_create_response(
            self,
            *,
            cdek_delivery: CdekDelivery,
            response: CDEKOrderCreateResponseSchema,
    ):
        for request in response.requests:
            self._save_request(
                cdek_delivery=cdek_delivery,
                cdek_uuid=response.entity["uuid"],
                request_type=request.type,
                state=request.state,
                date_time=request.date_time,
                response_data=response.model_dump(mode="json"),
            )

    def save_order_response(
            self,
            *,
            cdek_delivery: CdekDelivery,
            response: CDEKOrderResponseSchema,
    ):
        for request in response.requests:
            self._save_request(
                cdek_delivery=cdek_delivery,
                cdek_uuid=response.entity.uuid,
                request_type=request.type,
                state=request.state,
                date_time=request.date_time,
                errors=request.errors,
                response_data=response.model_dump(mode="json"),
            )


class CdekStatusService:

    def __init__(self):
        self.adapter = CDEKAdapter()
        self.request_log_service = CdekRequestLogService()
        self.status_service = CdekOrderStatusService()
        self.order_status_service = OrderStatusService()

    def get_order_delivery_status(
            self,
            *,
            response: CDEKOrderResponseSchema,
    ) -> OrderDeliveryStatus | None:
        """Возвращает внутренний статус для OrderDelivery на основе ответа CDEK."""

        if not response.entity.statuses:
            return None

        latest_status = max(
            response.entity.statuses,
            key=lambda status: status.date_time,
        )

        return CdekDeliveryStatusMapper.map(
            status_code=latest_status.code,
            status_name=latest_status.name,
        )

    def check_order(
        self,
        *,
        cdek_delivery: CdekDelivery,
    ) -> CDEKOrderResponseSchema:

        response = self.adapter.get_order_uuid(
            uuid=cdek_delivery.cdek_uuid,
        )

        self.request_log_service.save_order_response(
            cdek_delivery=cdek_delivery,
            response=response,
        )

        self.status_service.save_statuses(
            cdek_delivery=cdek_delivery,
            response=response,
        )

        status = self.get_order_delivery_status(
            response=response,
        )

        if status is not None:
            order_delivery = cdek_delivery.order_delivery

            if order_delivery.status != status:
                order_delivery.status = status
                order_delivery.save(
                    update_fields=["status"],
                )

                self.order_status_service.update_order_status(
                    order=order_delivery.order,
                )

        return response

    def get_create_request(
            self,
            response: CDEKOrderResponseSchema):
        """Получение последнего запроса CREATE из ответа CDEK."""
        for request in reversed(response.requests):
            if request.type == "CREATE":
                return request

        return None

    def confirm_cdek_delivery(
            self,
            *,
            cdek_delivery_id: int,
            cdek_number: str,
            total_sum: Decimal,
    ) -> bool:
        """Подтверждение доставки после успешной регистрации в CDEK."""
        with transaction.atomic():
            cdek_delivery = (
                CdekDelivery.objects
                .select_for_update()
                .select_related(
                    "order_delivery",
                    "order_delivery__order",
                )
                .get(id=cdek_delivery_id)
            )

            # Идемпотентность.
            # Если задача уже подтвердила/вернула заказ,
            # повторно ничего не делаем.
            if (
                    cdek_delivery.stock_status
                    != StockReservationStatus.RESERVED
            ):
                return False

            cdek_delivery.shipment_track_id = cdek_number
            cdek_delivery.shipment_price = total_sum
            cdek_delivery.stock_status = (
                StockReservationStatus.CONFIRMED
            )

            cdek_delivery.save(
                update_fields=[
                    "shipment_track_id",
                    "shipment_price",
                    "stock_status",
                ]
            )

            order_products = OrderProduct.objects.filter(
                order_delivery=cdek_delivery.order_delivery,
            )

            unique_product_ids = list(
                order_products.values_list(
                    "unique_product_id",
                    flat=True,
                ).distinct()
            )

            cart = cdek_delivery.order_delivery.order.owner.cart

            CartService.clear_items(
                cart=cart,
                unique_product_ids=unique_product_ids,
            )

            return True

    def release_cdek_delivery(
            self,
            *,
            cdek_delivery_id: int,
    ) -> bool:
        """Возврат товара на склад при ошибке регистрации CDEK."""
        with transaction.atomic():
            cdek_delivery = (
                CdekDelivery.objects
                .select_for_update()
                .select_related(
                    "order_delivery",
                    "order_delivery__order",
                )
                .get(id=cdek_delivery_id)
            )

            # Идемпотентность.
            if (
                    cdek_delivery.stock_status
                    != StockReservationStatus.RESERVED
            ):
                return False

            order_products = list(
                OrderProduct.objects.filter(
                    order_delivery=cdek_delivery.order_delivery,
                )
            )

            unique_product_ids = {
                order_product.unique_product_id
                for order_product in order_products
            }

            locked_products = StockService.lock_products(
                unique_product_ids=unique_product_ids,
            )

            for order_product in order_products:
                unique_product = locked_products.get(
                    order_product.unique_product_id
                )

                if unique_product is None:
                    raise ValueError(
                        "Товар "
                        f"id={order_product.unique_product_id} "
                        "не найден."
                    )

                StockService.increase(
                    unique_product=unique_product,
                    amount=order_product.amount,
                )

            cdek_delivery.stock_status = (
                StockReservationStatus.RELEASED
            )

            cdek_delivery.save(
                update_fields=["stock_status"]
            )

            return True

    def process(
        self,
        *,
        cdek_delivery_id: int,
    ) -> tuple[StockReservationStatus, list[dict] | None]:

        cdek_delivery = CdekDelivery.objects.get(
            id=cdek_delivery_id,
        )

        response = self.check_order(
            cdek_delivery=cdek_delivery,
        )

        create_request = self.get_create_request(response)

        if create_request is None:
            return StockReservationStatus.RESERVED, None

        if create_request.state == "ACCEPTED":
            return StockReservationStatus.RESERVED, None

        if create_request.state == "SUCCESSFUL":
            entity = response.entity

            if (
                entity.cdek_number is None
                or entity.delivery_detail is None
                or entity.delivery_detail.get("total_sum") is None
            ):
                raise ValueError(
                    "CDEK вернул SUCCESSFUL, "
                    "но не вернул cdek_number "
                    "или delivery_detail.total_sum."
                )

            self.confirm_cdek_delivery(
                cdek_delivery_id=cdek_delivery_id,
                cdek_number=entity.cdek_number,
                total_sum=entity.delivery_detail["total_sum"],
            )

            return StockReservationStatus.CONFIRMED, None

        self.release_cdek_delivery(
            cdek_delivery_id=cdek_delivery_id,
        )

        errors = [
            {
                "code": error.code,
                "message": error.message,
            }
            for error in create_request.errors
        ]

        return StockReservationStatus.RELEASED, errors