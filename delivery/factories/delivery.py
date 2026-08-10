"""
Для поддержки нескольких служб доставки.
Вернет нужный Adapter:DeliveryFactory.create(DeliveryType.CDEK) -> CDEKAdapter.
"""
from delivery.models import DeliveryType, CDEKTariff
from delivery.services.tariffs import CDEKTariffService
from delivery.tasks.tariffs import sync_cdek_tariffs
from seller.models import Shop
from seller.services import ShopDeliverySettingService
from django.core.cache import cache
from django.db import transaction


def initialize_cdek(shop):
    """
        Инициализация СДЭК.

        Если это первый магазин маркетплейса,
        использующий СДЭК, запускается синхронизация
        общего справочника тарифов.
        """

    has_other_cdek = Shop.objects.filter(
        carrier=DeliveryType.CDEK,
    ).exclude(
        pk=shop.pk,
    ).exists()

    if not has_other_cdek:
        transaction.on_commit(
            sync_cdek_tariffs.delay
        )


def cleanup_cdek(shop):
    """
    Очистка данных СДЭК.

    Выполняется при удалении магазина
    или смене службы доставки.
    """

    # удаляем персональные настройки магазина
    ShopDeliverySettingService().clear(shop)

    has_other_cdek = Shop.objects.filter(
        carrier=DeliveryType.CDEK,
    ).exclude(
        pk=shop.pk,
    ).exists()

    if has_other_cdek:
        return

    # последний магазин СДЭК удален

    # удаляем общий Redis-кэш;
    cache.delete(
        CDEKTariffService.CACHE_KEY
    )

    # удаляем общий справочник тарифов.
    CDEKTariff.objects.all().delete()


class DeliveryFactory:
    """ Фабрика инициализации служб доставки.
        Вызывает необходимую логику после создания магазина
        в зависимости от выбранной транспортной компании. """

    # Соответствие службы доставки и функции её инициализации.
    _handlers = {
        DeliveryType.CDEK: initialize_cdek,
    }

    _cleanup_handlers = {
        DeliveryType.CDEK: cleanup_cdek,
    }

    @classmethod
    def initialize(cls, shop):
        """ Выполняет инициализацию выбранной службы доставки.
        Если для перевозчика не зарегистрирован обработчик,
        никаких дополнительных действий не выполняется. """

        handler = cls._handlers.get(shop.carrier)

        if handler:
            handler(shop)

    @classmethod
    def cleanup(cls, shop, carrier=None):
        """ Выполняет очистку данных службы доставки.

        Если carrier не указан, используется текущий
        перевозчик магазина."""

        carrier = carrier or shop.carrier

        handler = cls._cleanup_handlers.get(carrier)

        if handler:
            handler(shop)