from celery import shared_task

from delivery.enums import StockReservationStatus
from delivery.kafka.producers import KafkaProducer
from delivery.kafka.schemas import CDEKOrderReadyEvent, CDEKOrderFailedEvent
from delivery.kafka.topics import KafkaTopic
from delivery.models import CdekDelivery
from delivery.services.order import CdekStatusService


@shared_task
def check_cdek_order_status(cdek_delivery_id: int):
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