from delivery.adapters.cdek import CDEKAdapter
from delivery.enums import StockReservationStatus
from delivery.models import CdekDelivery, CdekDeliveryStatusHistory, CdekRequestLog
from delivery.schemas.order import CDEKOrderResponseSchema, CDEKOrderCreateResponseSchema
from django.db import transaction
from decimal import Decimal

from order.models import OrderProduct
from product.services import CartService, StockService


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