"""
Для поддержки нескольких служб доставки.
Вернет нужный Adapter:DeliveryFactory.create(DeliveryType.CDEK) -> CDEKAdapter.
"""
from delivery.adapters.cdek import CDEKAdapter
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
        Отвечает за инициализацию, очистку и создание адаптеров."""

    # Соответствие службы доставки и функции её инициализации.
    _handlers = {
        DeliveryType.CDEK: initialize_cdek,
    }

    _cleanup_handlers = {
        DeliveryType.CDEK: cleanup_cdek,
    }

    # Реестр адаптеров
    _adapters = {
        DeliveryType.CDEK: CDEKAdapter,
        # Сюда будете добавлять новые: DeliveryType.POST: RussianPostAdapter,
    }

    @classmethod
    def initialize(cls, shop: Shop):
        """ Выполняет инициализацию выбранной службы доставки.
        Если для перевозчика не зарегистрирован обработчик,
        никаких дополнительных действий не выполняется. """

        handler = cls._handlers.get(shop.carrier)

        if handler:
            handler(shop)

    @classmethod
    def cleanup(cls, shop: Shop):
        """ Выполняет очистку данных службы доставки.

        Если carrier не указан, используется текущий
        перевозчик магазина."""

        handler = cls._cleanup_handlers.get(shop.carrier)

        if handler:
            handler(shop)

    @classmethod
    def get_adapter(cls, shop: Shop):
        """
        Возвращает экземпляр нужного адаптера по типу перевозчика.
        DeliveryFactory.get_adapter(DeliveryType.CDEK) -> CDEKAdapter()
        """
        adapter_class = cls._adapters.get(shop.carrier)

        if not adapter_class:
            raise NotImplementedError(f"Адаптер для carrier={shop.carrier} не реализован")

        return adapter_class()