from django.db import transaction
from delivery.models import CDEKTariff
from delivery.services.tariffs import CDEKTariffService
from seller.models import ShopDeliverySetting


class ShopDeliverySettingService:

    CACHE_KEY = "cdek:tariffs"


    def get_available_tariff_codes(self):
        """ Получение актуальных тарифов из Redis. """

        tariffs = CDEKTariffService().get_cached_tariffs()

        return {
            tariff["tariff_code"]
            for tariff in tariffs
        }

    @transaction.atomic
    def save(self, shop, tariff_codes):
        available_codes = self.get_available_tariff_codes()

        invalid_codes = set(tariff_codes) - available_codes

        if invalid_codes:
            raise ValueError(
                f"Недоступные тарифы: {invalid_codes}"
            )

        tariffs = CDEKTariff.objects.filter(
            tariff_code__in=tariff_codes
        )

        # не сохраняем историю выбора кодов продавцом
        ShopDeliverySetting.objects.filter(shop=shop).delete()

        ShopDeliverySetting.objects.bulk_create(
            [
                ShopDeliverySetting(
                    shop=shop,
                    tariff=tariff,
                )
                for tariff in tariffs
            ]
        )


    def get_shop_tariffs(self, shop):
        """
        Получение выбранных тарифов магазина.
        """

        return (
            ShopDeliverySetting.objects
            .filter(shop=shop)
            .select_related("tariff")
        )

    def clear(self, shop):
        """ Очистить настройки магазина"""
        ShopDeliverySetting.objects.filter(
            shop=shop
        ).delete()