from celery import shared_task

from delivery.enums import StockReservationStatus
from delivery.kafka.producers import KafkaProducer
from delivery.kafka.schemas import CDEKOrderReadyEvent, CDEKOrderFailedEvent
from delivery.kafka.topics import KafkaTopic
from delivery.models import CdekDelivery
from delivery.services.order import CdekStatusService
from order.enams import OrderDeliveryStatus


@shared_task
def check_cdek_order_status(cdek_delivery_id: int):
    cdek_delivery = (
        CdekDelivery.objects
        .select_related("order_delivery")
        .get(id=cdek_delivery_id)
    )

    if cdek_delivery.order_delivery.status == OrderDeliveryStatus.CANCELLED:
        return

    service = CdekStatusService()

    result, errors = service.process(
        cdek_delivery_id=cdek_delivery_id,
    )

    if result == StockReservationStatus.RESERVED:
        check_cdek_order_status.apply_async(
            args=[cdek_delivery_id],
            countdown=30,
        )
        return

    cdek_delivery = CdekDelivery.objects.get(
        id=cdek_delivery_id,
    )

    if result == StockReservationStatus.CONFIRMED:
        if cdek_delivery.shipment_track_id is None:
            raise ValueError(
                "У подтверждённой CDEK доставки "
                "отсутствует номер отправления."
            )
        event = CDEKOrderReadyEvent(
            cdek_delivery_id=cdek_delivery.id,
            cdek_uuid=cdek_delivery.cdek_uuid,
            cdek_number=str(cdek_delivery.shipment_track_id)
        )

        KafkaProducer().send(
            topic=KafkaTopic.CDEK_ORDER_READY,
            message=event.model_dump(),
        )

        return

    if result == StockReservationStatus.RELEASED:
        event = CDEKOrderFailedEvent(
            cdek_delivery_id=cdek_delivery.id,
            cdek_uuid=cdek_delivery.cdek_uuid,
            errors=errors or [],
        )
        KafkaProducer().send(
            topic=KafkaTopic.CDEK_ORDER_FAILED,
            message=event.model_dump(),
        )

        return


@shared_task
def check_cdek_order_deletion(
    cdek_delivery_id: int,
):
    service = CdekStatusService()

    result = service.check_order_deletion(
        cdek_delivery_id=cdek_delivery_id,
    )

    if result is False:
        check_cdek_order_deletion.apply_async(
            args=[cdek_delivery_id],
            countdown=30,
        )


@shared_task
def check_cdek_client_return_status(
    cdek_return_id: int,
):
    service = CdekStatusService()

    result = service.check_client_return(
        cdek_return_id=cdek_return_id,
    )

    if result is False:
        check_cdek_client_return_status.apply_async(
            args=[cdek_return_id],
            countdown=30,
        )