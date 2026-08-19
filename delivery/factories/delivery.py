"""
Для поддержки нескольких служб доставки.
"""
from delivery.models import DeliveryType, CDEKTariff
from delivery.services.tariffs import CDEKTariffService, CDEKDeliveryOptionsService, CDEKCalculateDeliveryService
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
    """ Фабрика служб доставки.

    Отвечает за выбор и инициализацию компонентов,
    соответствующих транспортной компании магазина:
    - обработчика инициализации;
    - обработчика очистки;
    - сервиса предварительного расчета доставки."""

    # Обработчики инициализации служб доставки.
    _handlers = {
        DeliveryType.CDEK: initialize_cdek,
    }

    # Обработчики очистки данных служб доставки.
    _cleanup_handlers = {
        DeliveryType.CDEK: cleanup_cdek,
    }

    # Сервисы предварительного расчета доставки.
    #
    # Каждый сервис инкапсулирует особенности конкретной ТК:
    # формат входных данных;
    # вызов соответствующего адаптера;
    # обработку ответа API;
    # фильтрацию тарифов;
    # преобразование ответа в единый DTO.
    _services = {
        DeliveryType.CDEK: CDEKDeliveryOptionsService,
    }

    # Сервисы расчета стоимости доставки по коду тарифа
    _code_tariff_services = {
        DeliveryType.CDEK: CDEKCalculateDeliveryService,
    }

    @classmethod
    def initialize(cls, shop: Shop):
        """ Выполняет инициализацию службы доставки,
        указанной у магазина.

        Если для перевозчика не зарегистрирован обработчик,
        дополнительные действия не выполняются. """

        handler = cls._handlers.get(shop.carrier)

        if handler:
            handler(shop)

    @classmethod
    def cleanup(cls, shop: Shop):
        """ Выполняет очистку данных службы доставки,
        указанной у магазина.

        Если для перевозчика не зарегистрирован обработчик,
        дополнительные действия не выполняются."""

        handler = cls._cleanup_handlers.get(shop.carrier)

        if handler:
            handler(shop)

    @classmethod
    def get_service(cls, shop: Shop):
        """ Возвращает сервис предварительного расчета доставки
        для транспортной компании магазина.

        Сервис инкапсулирует работу с соответствующим адаптером
        и особенности обработки ответа конкретной ТК."""
        service_class = cls._services.get(shop.carrier)

        if not service_class:
            raise NotImplementedError(
                f"Сервис предварительного расчета доставки для carrier={shop.carrier} не реализован"
            )

        return service_class()

    @classmethod
    def get_code_tariff_service(cls, shop: Shop):
        """ Возвращает сервис расчета доставки по коду тарифа
        для транспортной компании магазина.

        Сервис инкапсулирует работу с соответствующим адаптером
        и особенности обработки ответа конкретной ТК."""
        service_class = cls._code_tariff_services.get(shop.carrier)

        if not service_class:
            raise NotImplementedError(
                f"Сервис расчета доставки по коду тарифа для carrier={shop.carrier} не реализован"
            )

        return service_class()