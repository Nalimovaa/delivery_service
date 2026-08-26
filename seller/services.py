from django.db import transaction
from django.utils import timezone

from delivery.adapters.cdek import CDEKAdapter
from delivery.models import CDEKTariff
from delivery.services.locations import CDEKCityService, CDEKPostalCodeService
from delivery.services.tariffs import CDEKTariffService
from seller.models import CDEKShopDeliverySetting, Shop, SellerRequest, SellerRequestStatus
from users.models import Role, UserRole
from rest_framework.exceptions import ValidationError


class CDEKShopDeliverySettingService:

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
        CDEKShopDeliverySetting.objects.filter(shop=shop).delete()

        CDEKShopDeliverySetting.objects.bulk_create(
            [
                CDEKShopDeliverySetting(
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
            CDEKShopDeliverySetting.objects
            .filter(shop=shop)
            .select_related("tariff")
        )

    def clear(self, shop):
        """ Очистить настройки магазина"""
        CDEKShopDeliverySetting.objects.filter(
            shop=shop
        ).delete()


class SellerService:
    """Service for managing Seller role."""

    @staticmethod
    def assign_role(user):
        """Assign Seller role to the user."""
        seller_role, _ = Role.objects.get_or_create(
            name="Seller",
        )

        UserRole.objects.get_or_create(
            user=user,
            role=seller_role,
        )

    @staticmethod
    def remove_role_if_no_shops(user):
        """Remove Seller role if the user no longer owns any shops."""

        has_shops = Shop.objects.filter(
            owner=user,
        ).exists()

        if has_shops:
            return

        seller_role = Role.objects.filter(
            name="Seller",
        ).first()

        if seller_role:
            UserRole.objects.filter(
                user=user,
                role=seller_role,
            ).delete()




class SellerRequestService:
    """Сервис для работы с заявками на получение роли Seller."""

    @staticmethod
    def create(user):
        # Пользователь уже продавец
        if UserRole.objects.filter(
            user=user,
            role__name="Seller",
        ).exists():
            raise ValueError(
                "Пользователь уже является продавцом."
            )

        # Есть активная заявка на рассмотрении
        if SellerRequest.objects.filter(
            user=user,
            status=SellerRequestStatus.PENDING,
        ).exists():
            raise ValueError(
                "Заявка уже находится на рассмотрении."
            )

        # После REJECTED можно подать новую заявку
        return SellerRequest.objects.create(
            user=user,
            status=SellerRequestStatus.PENDING,
            rejection_reason=None,
        )

    @staticmethod
    @transaction.atomic
    def approve(seller_request: SellerRequest):
        if seller_request.status != SellerRequestStatus.PENDING:
            raise ValueError(
                "Можно одобрить только заявку, находящуюся на рассмотрении."
            )

        role = Role.objects.get(name="Seller")

        UserRole.objects.get_or_create(
            user=seller_request.user,
            role=role,
        )

        seller_request.status = SellerRequestStatus.APPROVED
        seller_request.rejection_reason = None
        seller_request.save(
            update_fields=[
                "status",
                "rejection_reason",
                "updated_at",
            ]
        )

        return seller_request

    @staticmethod
    @transaction.atomic
    def reject(
        seller_request: SellerRequest,
        reason: str,
    ):
        if seller_request.status != SellerRequestStatus.PENDING:
            raise ValueError(
                "Можно отклонить только заявку, находящуюся на рассмотрении."
            )

        if not reason or not reason.strip():
            raise ValueError(
                "Необходимо указать причину отказа."
            )

        seller_request.status = SellerRequestStatus.REJECTED
        seller_request.rejection_reason = reason.strip()

        seller_request.save(
            update_fields=[
                "status",
                "rejection_reason",
                "updated_at",
            ]
        )

        return seller_request



class CDEKShopValidationService:
    """
    Сервис валидации данных магазина для доставки CDEK.

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
        location_from: str,
        location_from_region: str,
        location_from_district: str | None,
        location_from_country: str,
        postal_code: str,
    ) -> None:
        """
        Проверяет данные магазина для доставки CDEK.

        Если населенный пункт или почтовый индекс
        не соответствуют данным CDEK, выбрасывается ValidationError.
        """

        city = self.city_service.get_city(
            city=location_from,
            region=location_from_region,
            sub_region=location_from_district,
            country=location_from_country,
        )

        if city is None:
            city = self._get_city_from_cdek(
                city=location_from,
                region=location_from_region,
                sub_region=location_from_district,
                country=location_from_country,
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
