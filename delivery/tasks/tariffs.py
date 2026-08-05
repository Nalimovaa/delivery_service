from celery import shared_task

from delivery.models import DeliveryType
from delivery.services.tariffs import CDEKTariffService
import logging

from seller.models import Shop

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_cdek_tariffs():
    """
    Синхронизация тарифов CDEK.

    Получает все доступные тарифы по договору продавца из API СДЭК,
    обновляет базу данных и кэш Redis.
    """

    if not Shop.objects.filter(
            carrier=DeliveryType.CDEK
    ).exists():
        logger.info(
            "No shops with CDEK carrier. Skip sync."
        )
        return {
            "processed": 0,
            "status": "skipped",
        }

    result = CDEKTariffService().sync_cdek_tariffs()

    logger.info(
        "Processed %s tariffs",
        result["processed"],
    )

    return result