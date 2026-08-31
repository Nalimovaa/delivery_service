from django.core.cache import cache

from delivery.adapters.cdek import CDEKAdapter
from delivery.models import CDEKCity, CDEKDeliveryPoint
from delivery.schemas.locations import CDEKCitiesSchema, CDEKDeliveryPointSchema, CDEKPostalCodesResponseSchema
from rest_framework.exceptions import ValidationError


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

    def get_city(
            self,
            *,
            city: str,
            region: str,
            sub_region: str | None = None,
            country: str = "Россия",
    ) -> CDEKCity | None:
        """
        Возвращает населенный пункт CDEK.

        Сначала выполняется поиск в Redis.
        Если Redis пуст — поиск выполняется в PostgreSQL.
        """

        city = city.strip()
        region = region.strip()
        country = country.strip()

        if sub_region:
            sub_region = sub_region.strip()

        cached_cities = self.get_cached_cities()

        if cached_cities:
            matches = [
                item
                for item in cached_cities
                if (
                        item["city"].casefold() == city.casefold()
                        and item["region"].casefold() == region.casefold()
                        and item["country"].casefold() == country.casefold()
                        and (
                                sub_region is None
                                or (
                                        item["sub_region"]
                                        and item["sub_region"].casefold()
                                        == sub_region.casefold()
                                )
                        )
                )
            ]

            if len(matches) == 1:
                return CDEKCity.objects.filter(
                    code=matches[0]["code"],
                    is_active=True,
                ).first()

            if len(matches) > 1:
                raise ValidationError(
                    {
                        "location_from": (
                            "Найдено несколько населенных пунктов "
                            "CDEK с указанными параметрами."
                        )
                    }
                )

        queryset = CDEKCity.objects.filter(
            city__iexact=city,
            region__iexact=region,
            country__iexact=country,
            is_active=True,
        )

        if sub_region:
            queryset = queryset.filter(
                sub_region__iexact=sub_region,
            )

        count = queryset.count()

        if count == 1:
            return queryset.first()

        if count > 1:
            raise ValidationError(
                {
                    "location_from": (
                        "Найдено несколько населенных пунктов "
                        "CDEK с указанными параметрами."
                    )
                }
            )

        return None

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

    def get_delivery_point(
            self,
            code: str,
    ):
        """
        Возвращает активный пункт CDEK.

        Сначала Redis, затем PostgreSQL.
        """

        delivery_points = self.get_delivery_points()

        for point in delivery_points:
            if str(point["code"]) == str(code):
                return point

        raise ValidationError(
            {
                "delivery_point": (
                    "Выбранный пункт CDEK "
                    "не найден или неактивен."
                )
            }
        )



class CDEKPostalCodeService:
    """
    Сервис для получения почтовых индексов населенного пункта CDEK.

    Получает индексы через API CDEK и кэширует результат
    в Redis для повторного использования.
    """

    CACHE_KEY_PREFIX = "cdek:postal_codes"
    CACHE_TIMEOUT = 60 * 60 * 24

    def fetch_postalcodes(
        self,
        code: int,
    ) -> CDEKPostalCodesResponseSchema:
        """Получение почтовых индексов из API СДЭК."""

        adapter = CDEKAdapter()

        return adapter.get_postalcodes(
            code=code,
        )

    def update_cache(
        self,
        code: int,
        postal_codes: list[str],
    ):
        """Сохранение почтовых индексов в Redis."""

        cache.set(
            self.get_cache_key(code),
            postal_codes,
            timeout=self.CACHE_TIMEOUT,
        )

    def get_cache_key(
        self,
        code: int,
    ) -> str:
        """Формирование ключа Redis для населенного пункта."""

        return (
            f"{self.CACHE_KEY_PREFIX}:{code}"
        )

    def get_postalcodes(
        self,
        code: int,
    ) -> list[str]:
        """
        Получение почтовых индексов населенного пункта.

        Сначала выполняется поиск в Redis.
        Если данных в кэше нет, выполняется запрос
        к API CDEK и результат сохраняется в Redis.
        """

        cached_postal_codes = cache.get(
            self.get_cache_key(code),
        )

        if cached_postal_codes is not None:
            return cached_postal_codes

        response = self.fetch_postalcodes(
            code=code,
        )

        postal_codes = response.postal_codes

        self.update_cache(
            code=code,
            postal_codes=postal_codes,
        )

        return postal_codes


class CDEKLocationValidationService:
    """
    Сервис валидации данных локации для доставки CDEK.

    Может использоваться для валидации данных:
    - магазина;
    - покупателя.

    Проверяет переданные данные:
    - населенный пункт;
    - регион;
    - район;
    - страну;
    - почтовый индекс;
    - ПВЗ.

    Сервис не определяет, какие поля должны быть
    заполнены одновременно. Он проверяет только те
    данные, которые были переданы.
    """

    def __init__(self):
        self.city_service = CDEKCityService()
        self.postal_code_service = CDEKPostalCodeService()
        self.delivery_point_service = CDEKDeliveryPointService()
        self.adapter = CDEKAdapter()

    def validate(
            self,
            *,
            location: str| None,
            location_region: str| None,
            location_district: str | None,
            location_country: str| None,
            postal_code: str| None,
            delivery_point: str | None,
    ) -> None:
        """
        Проверяет переданные данные локации.

        Каждое поле проверяется только если оно передано.
        Взаимоисключающая логика находится на уровне
        сервиса создания отправления.
        """
        if location:
            if not postal_code:
                raise ValidationError(
                    {
                        "postal_code": (
                            "Почтовый индекс обязателен "
                            "для проверки населенного пункта."
                        )
                    }
                )

            city = self.city_service.get_city(
                city=location,
                region=location_region,
                sub_region=location_district,
                country=location_country,
            )

            if city is None:
                city = self._get_city_from_cdek(
                    city=location,
                    region=location_region,
                    sub_region=location_district,
                    country=location_country,
                )

            if city is None:
                raise ValidationError(
                    {
                        "location_from": (
                            "Населенный пункт с указанными "
                            "параметрами не найден в CDEK."
                        )
                    }
                )

            postal_codes = self.postal_code_service.get_postalcodes(
                code=city.code,
            )

            if postal_code.strip() not in postal_codes:
                raise ValidationError(
                    {
                        "postal_code": (
                            "Почтовый индекс не соответствует "
                            "населенному пункту CDEK."
                        )
                    }
                )

        # Если передан ПВЗ, проверяем его отдельно.
        if delivery_point:
            self.delivery_point_service.get_delivery_point(
                delivery_point,
            )

    def _get_city_from_cdek(
            self,
            *,
            city: str,
            region: str,
            sub_region: str | None,
            country: str,
    ):
        """
        Получает населенный пункт напрямую из API CDEK.

        Используется как fallback, если населенный пункт
        отсутствует в локальном справочнике.
        """

        try:
            cities = self.adapter.get_cities(
                country_codes="RU",
                city=city.strip(),
            )
        except Exception:
            return None

        matches = [
            item
            for item in cities
            if (
                    item.city.casefold() == city.strip().casefold()
                    and item.region.casefold()
                    == region.strip().casefold()
                    and item.country.casefold()
                    == country.strip().casefold()
                    and (
                            sub_region is None
                            or (
                                    item.sub_region
                                    and item.sub_region.casefold()
                                    == sub_region.strip().casefold()
                            )
                    )
            )
        ]

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            raise ValidationError(
                {
                    "location_from": (
                        "Найдено несколько населенных пунктов "
                        "CDEK с указанными параметрами."
                    )
                }
            )

        return None
