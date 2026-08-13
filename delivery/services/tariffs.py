from django.core.cache import cache
from delivery.adapters.cdek import CDEKAdapter
from delivery.models import CDEKTariff
from delivery.schemas.tariffs import AvailableTariffsResponseSchema, TariffListResponseSchema
from seller.models import Shop
from typing import List, Dict, Any, Optional


class CDEKTariffService:
    CACHE_KEY = "cdek:tariffs"
    CACHE_TIMEOUT = 60 * 60 * 24

    def fetch_tariffs(self) -> AvailableTariffsResponseSchema:
        """ Получение списка тарифов из API СДЭК. """
        adapter = CDEKAdapter()
        return adapter.get_all_tariffs()

    def prepare_tariffs(
            self,
            response: AvailableTariffsResponseSchema
    ):
        """ Генератор подготовленных данных для сохранения в БД. """

        for tariff in response.tariff_codes:

            for mode in tariff.delivery_modes:

                if mode.tariff_code is None:
                    continue

                yield {
                    "tariff_code": mode.tariff_code,
                    "tariff_name": tariff.tariff_name,
                    "delivery_mode": mode.delivery_mode,
                    "delivery_mode_name": mode.delivery_mode_name,
                    "weight_min": tariff.weight_min,
                    "weight_max": tariff.weight_max,
                    "length_max": tariff.length_max,
                    "width_max": tariff.width_max,
                    "height_max": tariff.height_max,
                    "is_active": True,
                }

    def save_tariffs(self, tariffs):
        """ Массовое сохранение и обновление тарифов. """
        CDEKTariff.objects.bulk_update_or_create(tariffs)

    def deactivate_missing(self, active_tariff_codes):
        """ Деактивация тарифов, отсутствующих в новом ответе API. """
        CDEKTariff.objects.exclude(
            tariff_code__in=active_tariff_codes
        ).update(is_active=False)

    def update_cache(self):
        """ Кэширование актуальных тарифов. """
        cache.set(
            self.CACHE_KEY,
            list(
                CDEKTariff.objects.filter(
                    is_active=True
                ).values(
                    "tariff_code",
                    "tariff_name",
                    "delivery_mode",
                    "delivery_mode_name",
                    "weight_min",
                    "weight_max",
                    "length_max",
                    "width_max",
                    "height_max",
                )
            ),
            timeout=self.CACHE_TIMEOUT,
        )

    def sync_cdek_tariffs(self):
        """ Полная синхронизация тарифов. """
        response = self.fetch_tariffs() # Получение данных из API СДЭК

        tariffs = list(self.prepare_tariffs(response)) # Подготовка данных для сохранения в БД

        active_codes = {
            tariff["tariff_code"] # итерируемся по каждому тарифу из API СДЭКа
            for tariff in tariffs
        }

        self.save_tariffs(tariffs) # Сохранение тарифов в БД из API СДЭК

        self.deactivate_missing(active_codes) # Деактивация тарифов в БД, отсутствующих в новом ответе API

        self.update_cache() # Обновление кэша с актуальными тарифами

        return {
            "processed": len(tariffs),
        }

    def get_cached_tariffs(self):
        """ Получение всех актуальных тарифов по договору продавца из Redis. """
        return cache.get(self.CACHE_KEY, [])


class DeliveryOptionsService:
    @staticmethod
    def process_cdek_response(
        shop: Shop,
        response: TariffListResponseSchema,
    ) -> List[Dict[str, Any]]:
        """
        Обрабатывает ответ от CDEKAdapter.pre_calculate_delivery,
        фильтрует по разрешённым тарифам магазина и приводит к единому формату.
        """
        # Получаем разрешённые коды тарифов из настроек магазина
        allowed_codes = set(
            shop.delivery_settings.values_list('tariff__tariff_code', flat=True)
        )
        if not allowed_codes:
            return []

        # Кэш названий тарифов (можно получить из CDEKTariffService)
        tariff_names = {
            t.tariff_code: t.tariff_name
            for t in CDEKTariff.objects.filter(tariff_code__in=allowed_codes)
        }

        options = []
        for tariff_item in response.tariff_codes:
            if tariff_item.status != 'true':
                continue
            code = int(tariff_item.tariff_code)
            if code not in allowed_codes:
                continue
            res = tariff_item.result
            options.append({
                'tariff_code': str(code),
                'tariff_name': tariff_names.get(code, f'Тариф {code}'),
                'delivery_sum': res.delivery_sum,
                'period_min': res.period_min,
                'period_max': res.period_max,
                'delivery_date_range': res.delivery_date_range.dict() if res.delivery_date_range else None,
                'total_sum': res.total_sum,
                'currency': res.currency,
            })
        return options
