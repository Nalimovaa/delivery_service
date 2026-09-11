from order.enams import OrderStatus, OrderDeliveryStatus
from order.models import Order


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