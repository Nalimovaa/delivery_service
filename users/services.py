from delivery.adapters.cdek import CDEKAdapter
from delivery.services.locations import CDEKCityService, CDEKPostalCodeService
from rest_framework.exceptions import ValidationError


class CDEKUserValidationService:
    """
    Сервис валидации данных покупателя для доставки CDEK.

    Проверяет:
    - населенный пункт;
    - регион;
    - район;
    - страну;
    - почтовый индекс.

    Для существующего справочника сначала используется
    CDEKCityService (Redis/PostgreSQL).

    Если населенный пункт не найден в локальном справочнике,
    выполняется прямой запрос к API CDEK. Это необходимо
    при создании первого магазина CDEK, когда справочник
    еще не был синхронизирован.
    """

    def __init__(self):
        self.city_service = CDEKCityService()
        self.postal_code_service = CDEKPostalCodeService()
        self.adapter = CDEKAdapter()

    def validate(
        self,
        *,
        location_to: str,
        location_to_region: str,
        location_to_district: str | None,
        location_to_country: str,
        postal_code: str | None,
    ) -> None:
        """
        Проверяет данные пользователя для доставки CDEK.

        Если населенный пункт или почтовый индекс
        не соответствуют данным CDEK, выбрасывается ValidationError.
        """

        city = self.city_service.get_city(
            city=location_to,
            region=location_to_region,
            sub_region=location_to_district,
            country=location_to_country,
        )

        if city is None:
            city = self._get_city_from_cdek(
                city=location_to,
                region=location_to_region,
                sub_region=location_to_district,
                country=location_to_country,
            )

        if city is None:
            raise ValidationError(
                {
                    "location_to": (
                        "Населенный пункт с указанными "
                        "параметрами не найден в CDEK."
                    )
                }
            )

        if postal_code:
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
                    "location_to": (
                        "Найдено несколько населенных пунктов "
                        "CDEK с указанными параметрами."
                    )
                }
            )

        return None