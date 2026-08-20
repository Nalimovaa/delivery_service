from django.core.cache import cache

from delivery.adapters.cdek import CDEKAdapter
from delivery.models import CDEKCity
from delivery.schemas.locations import CDEKCitiesSchema


class CDEKCityService:
    """Отвечает за синхронизацию населенных пунктов CDEK
    из API в БД и кэш Redis."""

    CACHE_KEY = "cdek:cities"
    CACHE_TIMEOUT = 60 * 60 * 24

    def fetch_cities(self) -> list[CDEKCitiesSchema]:
        """Получение списка населенных пунктов из API СДЭК."""
        adapter = CDEKAdapter()

        return adapter.get_cities()

    def prepare_cities(
            self,
            response: list[CDEKCitiesSchema],
    ):
        """Генератор подготовленных данных для сохранения в БД."""

        for city in response:
            yield {
                "code": city.code,
                "city_uuid": city.city_uuid,
                "city": city.city,
                "fias_guid": city.fias_guid,
                "country_code": city.country_code,
                "country": city.country,
                "region": city.region,
                "region_code": city.region_code,
                "sub_region": city.sub_region,
                "longitude": city.longitude,
                "latitude": city.latitude,
                "time_zone": city.time_zone,
                "payment_limit": city.payment_limit,
                "is_active": True,
            }

    def save_cities(self, cities):
        """Массовое сохранение и обновление населенных пунктов."""
        CDEKCity.objects.bulk_update_or_create(
            cities,
        )

    def deactivate_missing(self, active_city_codes):
        """Деактивация населенных пунктов,
        отсутствующих в новом ответе API."""
        CDEKCity.objects.exclude(
            code__in=active_city_codes,
        ).update(
            is_active=False,
        )

    def update_cache(self):
        """Кэширование актуальных населенных пунктов."""

        cache.set(
            self.CACHE_KEY,
            list(
                CDEKCity.objects.filter(
                    is_active=True,
                ).values(
                    "code",
                    "city_uuid",
                    "city",
                    "fias_guid",
                    "country_code",
                    "country",
                    "region",
                    "region_code",
                    "sub_region",
                    "longitude",
                    "latitude",
                    "time_zone",
                    "payment_limit",
                )
            ),
            timeout=self.CACHE_TIMEOUT,
        )

    def sync_cdek_cities(self):
        """Полная синхронизация населенных пунктов."""

        # Получение данных из API СДЭК
        response = self.fetch_cities()

        # Подготовка данных для сохранения в БД
        cities = list(
            self.prepare_cities(response)
        )

        active_codes = {
            city["code"]
            for city in cities
        }

        # Сохранение населенных пунктов в БД
        self.save_cities(
            cities,
        )

        # Деактивация отсутствующих в новом ответе
        self.deactivate_missing(
            active_codes,
        )

        # Обновление Redis-кэша
        self.update_cache()

        return {
            "processed": len(cities),
        }

    def get_cached_cities(self):
        """Получение всех актуальных населенных пунктов из Redis."""
        return cache.get(
            self.CACHE_KEY,
            [],
        )