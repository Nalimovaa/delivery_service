from django.core.cache import cache

from delivery.adapters.cdek import CDEKAdapter
from delivery.models import CDEKCity, CDEKDeliveryPoint
from delivery.schemas.locations import CDEKCitiesSchema, CDEKDeliveryPointSchema


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


from django.core.cache import cache



class CDEKDeliveryPointService:
    """Отвечает за синхронизацию ПВЗ CDEK
    из API в БД и кэш Redis."""

    CACHE_KEY = "cdek:delivery_points"
    CACHE_TIMEOUT = 60 * 60 * 24

    def fetch_delivery_points(
            self,
    ) -> list[CDEKDeliveryPointSchema]:
        """Получение списка ПВЗ из API СДЭК."""
        adapter = CDEKAdapter()

        return adapter.get_delivery_points()

    def prepare_delivery_points(
            self,
            response: list[CDEKDeliveryPointSchema],
    ):
        """Генератор подготовленных данных для сохранения в БД."""

        for point in response:
            yield {
                "code": point.code,
                "name": point.name,
                "uuid": point.uuid,
                "address_comment": point.address_comment,
                "nearest_station": point.nearest_station,
                "nearest_metro_station": point.nearest_metro_station,
                "work_time": point.work_time,
                "email": point.email,
                "note": point.note,
                "type": point.type,
                "owner_code": point.owner_code,
                "take_only": point.take_only,
                "is_handout": point.is_handout,
                "is_reception": point.is_reception,
                "is_dressing_room": point.is_dressing_room,
                "is_ltl": point.is_ltl,
                "have_cashless": point.have_cashless,
                "have_cash": point.have_cash,
                "have_fast_payment_system": (
                    point.have_fast_payment_system
                ),
                "allowed_cod": point.allowed_cod,
                "office_image_list": [
                    image.url
                    for image in point.office_image_list
                ],
                "work_time_list": [
                    {
                        "day": work_time.day,
                        "time": work_time.time,
                    }
                    for work_time in point.work_time_list
                ],
                "work_time_exception_list": (
                    point.work_time_exception_list
                ),
                "status": point.status,
                "country_code": point.location.country_code,
                "region_code": point.location.region_code,
                "region": point.location.region,
                "city_code": point.location.city_code,
                "city": point.location.city,
                "postal_code": point.location.postal_code,
                "longitude": point.location.longitude,
                "latitude": point.location.latitude,
                "address": point.location.address,
                "address_full": point.location.address_full,
                "city_uuid": point.location.city_uuid,
                "ltl_acceptance_partners": (
                    point.ltl_acceptance_partners
                ),
                "ltl_issuance_partners": (
                    point.ltl_issuance_partners
                ),
                "fulfillment": point.fulfillment,
                "is_active": True,
            }

    def save_delivery_points(self, delivery_points):
        """Массовое сохранение и обновление ПВЗ."""
        CDEKDeliveryPoint.objects.bulk_update_or_create(
            delivery_points,
        )

    def deactivate_missing(self, active_codes):
        """Деактивация ПВЗ, отсутствующих в новом ответе API."""
        CDEKDeliveryPoint.objects.exclude(
            code__in=active_codes,
        ).update(
            is_active=False,
        )

    def update_cache(self):
        """Кэширование актуальных ПВЗ."""

        cache.set(
            self.CACHE_KEY,
            list(
                CDEKDeliveryPoint.objects.filter(
                    is_active=True,
                ).values(
                    "code",
                    "name",
                    "uuid",
                    "type",
                    "owner_code",
                    "status",
                    "is_handout",
                    "is_reception",
                    "allowed_cod",
                    "country_code",
                    "region_code",
                    "region",
                    "city_code",
                    "city",
                    "postal_code",
                    "longitude",
                    "latitude",
                    "address",
                    "address_full",
                    "city_uuid",
                )
            ),
            timeout=self.CACHE_TIMEOUT,
        )

    def sync_cdek_delivery_points(self):
        """Полная синхронизация ПВЗ CDEK."""

        # Получение данных из API СДЭК
        response = self.fetch_delivery_points()

        # Подготовка данных для сохранения в БД
        delivery_points = list(
            self.prepare_delivery_points(response)
        )

        active_codes = {
            delivery_point["code"]
            for delivery_point in delivery_points
        }

        # Сохранение ПВЗ в БД
        self.save_delivery_points(
            delivery_points,
        )

        # Деактивация отсутствующих в новом ответе
        self.deactivate_missing(
            active_codes,
        )

        # Обновление Redis-кэша
        self.update_cache()

        return {
            "processed": len(delivery_points),
        }

    def get_cached_delivery_points(self):
        """Получение всех актуальных ПВЗ из Redis."""
        return cache.get(
            self.CACHE_KEY,
            [],
        )

    def get_delivery_points(self):
        """
        Получение актуальных ПВЗ.

        Сначала используется Redis.
        Если кэш отсутствует, данные получаются из PostgreSQL
        и сохраняются в Redis.
        """

        delivery_points = cache.get(
            self.CACHE_KEY,
        )

        if delivery_points is not None:
            return delivery_points

        delivery_points = list(
            CDEKDeliveryPoint.objects.filter(
                is_active=True,
            ).values(
                "code",
                "name",
                "uuid",
                "type",
                "owner_code",
                "status",
                "is_handout",
                "is_reception",
                "allowed_cod",
                "country_code",
                "region_code",
                "region",
                "city_code",
                "city",
                "postal_code",
                "longitude",
                "latitude",
                "address",
                "address_full",
                "city_uuid",
            )
        )

        cache.set(
            self.CACHE_KEY,
            delivery_points,
            timeout=self.CACHE_TIMEOUT,
        )

        return delivery_points