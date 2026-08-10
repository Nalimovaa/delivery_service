""" docker exec -it delivery_service-web-1 python manage.py test seller.tests.test_services """

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from delivery.enums import DeliveryType
from delivery.models import CDEKTariff
from seller.models import Shop, ShopDeliverySetting
from seller.services import ShopDeliverySettingService, SellerService
from users.models import User, Role, UserRole


class TestShopDeliverySettingService(TestCase):
    """
    Тесты сервиса ShopDeliverySettingService.

    Проверяется:
    - сохранение выбранных тарифов магазина;
    - проверка доступности тарифов перед сохранением;
    - получение выбранных тарифов магазина;
    - удаление сохраненных настроек магазина.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.shop = Shop.objects.create(
            owner=self.user,
            name="Shop",
            carrier=DeliveryType.CDEK,
        )

        self.tariff = CDEKTariff.objects.create(
            tariff_code=499,
            tariff_name="Business",
            delivery_mode=1,
            delivery_mode_name="дверь-дверь",
            weight_min=Decimal("0.000"),
            weight_max=Decimal("1000.000"),
            length_max=1000,
            width_max=1000,
            height_max=1000,
            is_active=True,
        )

        self.service = ShopDeliverySettingService()

    @patch.object(
        ShopDeliverySettingService,
        "get_available_tariff_codes",
    )
    def test_save_tariffs(self, mocked_codes):
        """Проверяет успешное сохранение выбранных тарифов магазина."""

        mocked_codes.return_value = {499}

        self.service.save(
            shop=self.shop,
            tariff_codes=[499],
        )

        self.assertEqual(
            ShopDeliverySetting.objects.count(),
            1,
        )

    @patch.object(
        ShopDeliverySettingService,
        "get_available_tariff_codes",
    )
    def test_invalid_tariff(self, mocked_codes):
        """Проверяет, что при выборе недоступного тарифа возникает ValueError."""

        mocked_codes.return_value = {499}

        with self.assertRaises(ValueError):
            self.service.save(
                shop=self.shop,
                tariff_codes=[111],
            )

    def test_get_shop_tariffs(self):
        """Проверяет получение списка тарифов, выбранных магазином."""

        ShopDeliverySetting.objects.create(
            shop=self.shop,
            tariff=self.tariff,
        )

        tariffs = self.service.get_shop_tariffs(
            self.shop,
        )

        self.assertEqual(
            tariffs.count(),
            1,
        )

    def test_clear(self):
        """Проверяет удаление всех сохраненных тарифов магазина."""

        ShopDeliverySetting.objects.create(
            shop=self.shop,
            tariff=self.tariff,
        )

        self.service.clear(
            self.shop,
        )

        self.assertEqual(
            ShopDeliverySetting.objects.count(),
            0,
        )


class TestSellerService(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.role = Role.objects.create(
            name="Seller",
        )

    def test_assign_role(self):
        SellerService.assign_role(
            self.user,
        )

        self.assertTrue(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).exists()
        )

    def test_remove_role_if_no_shops(self):
        UserRole.objects.create(
            user=self.user,
            role=self.role,
        )

        SellerService.remove_role_if_no_shops(
            self.user,
        )

        self.assertFalse(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).exists()
        )

    def test_keep_role_if_user_has_shop(self):
        UserRole.objects.create(
            user=self.user,
            role=self.role,
        )

        Shop.objects.create(
            owner=self.user,
            name="Test shop",
            carrier=DeliveryType.CDEK,
        )

        SellerService.remove_role_if_no_shops(
            self.user,
        )

        self.assertTrue(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).exists()
        )
