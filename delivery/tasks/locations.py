import logging
from celery import shared_task
from delivery.models import DeliveryType
from delivery.services.locations import CDEKCityService, CDEKDeliveryPointService
from seller.models import Shop


logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_cdek_cities():
    """
    Синхронизация населенных пунктов CDEK.

    Получает список населенных пунктов из API СДЭК,
    обновляет базу данных и кэш Redis.
    """

    if not Shop.objects.filter(
        carrier=DeliveryType.CDEK
    ).exists():
        logger.info(
            "No shops with CDEK carrier. Skip cities sync."
        )
        return {
            "processed": 0,
            "status": "skipped",
        }

    result = CDEKCityService().sync_cdek_cities()

    logger.info(
        "Processed %s CDEK cities",
        result["processed"],
    )

    return result


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_cdek_delivery_points():
    """
    Синхронизация пунктов выдачи/приема CDEK.

    Получает список ПВЗ из API СДЭК,
    обновляет базу данных и кэш Redis.
    """

    if not Shop.objects.filter(
        carrier=DeliveryType.CDEK
    ).exists():
        logger.info(
            "No shops with CDEK carrier. Skip delivery points sync."
        )
        return {
            "processed": 0,
            "status": "skipped",
        }

    result = CDEKDeliveryPointService().sync_cdek_delivery_points()

    logger.info(
        "Processed %s CDEK delivery points",
        result["processed"],
    )

    return result