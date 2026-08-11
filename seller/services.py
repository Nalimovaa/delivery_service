from django.db import transaction
from django.utils import timezone
from delivery.models import CDEKTariff
from delivery.services.tariffs import CDEKTariffService
from seller.models import ShopDeliverySetting, Shop, SellerRequest, SellerRequestStatus
from users.models import Role, UserRole


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
