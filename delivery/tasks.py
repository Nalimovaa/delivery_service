from celery import shared_task
from delivery.services.tariffs import TariffService


@shared_task
def sync_cdek_tariffs():
    TariffService().sync_cdek_tariffs()