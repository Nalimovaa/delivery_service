from delivery.models import OrderDelivery
from order.enams import OrderStatus, OrderDeliveryStatus, ReturnRequestStatus
from order.models import Order, ReturnRequest
from rest_framework.exceptions import ValidationError


class OrderStatusService:
    """
    Сервис для обновления статуса заказа на основе статусов всех его доставок.
    """

    @staticmethod
    def update_order_status(
        *,
        order: Order,
    ) -> OrderStatus:

        statuses = list(
            order.deliveries.values_list(
                "status",
                flat=True,
            )
        )

        if not statuses:
            return order.status

        if all(
            status == OrderDeliveryStatus.PROCESSING
            for status in statuses
        ):
            new_status = OrderStatus.PROCESSING

        elif all(
                status == OrderDeliveryStatus.CANCELLED
                for status in statuses
        ):
            new_status = OrderStatus.CANCELLED

        elif all(
            status == OrderDeliveryStatus.DELIVERED
            for status in statuses
        ):
            new_status = OrderStatus.COMPLETED

        elif all(
            status == OrderDeliveryStatus.FAILED
            for status in statuses
        ):
            new_status = OrderStatus.FAILED

        elif any(
            status == OrderDeliveryStatus.FAILED
            for status in statuses
        ):
            new_status = OrderStatus.PARTIALLY_FAILED

        elif any(
            status == OrderDeliveryStatus.DELIVERED
            for status in statuses
        ):
            new_status = OrderStatus.PARTIALLY_DELIVERED

        elif all(
            status == OrderDeliveryStatus.CONFIRMED
            for status in statuses
        ):
            new_status = OrderStatus.CONFIRMED

        else:
            new_status = OrderStatus.PROCESSING

        if order.status != new_status:
            order.status = new_status
            order.save(update_fields=["status"])

        return new_status


class ReturnRequestService:
    """
    Сервис для создания запроса покупателя
    на возврат заказа магазину.
    """

    @staticmethod
    def create(
        *,
        user,
        order_delivery: OrderDelivery,
        reason: str,
    ) -> ReturnRequest:

        if order_delivery.order.owner_id != user.id:
            raise ValidationError(
                "Вы не можете оформить возврат этого заказа."
            )

        if order_delivery.status != OrderDeliveryStatus.DELIVERED:
            raise ValidationError(
                "Возврат можно оформить только для доставленного заказа."
            )

        return ReturnRequest.objects.create(
            order_delivery=order_delivery,
            owner=user,
            status=ReturnRequestStatus.REQUESTED,
            reason=reason,
        )