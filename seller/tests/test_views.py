""" docker exec -it delivery_service-web-1 python manage.py test seller.tests.test_views """

from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import CDEKTariff
from seller.models import Shop, ShopDeliverySetting
from users.models import User


class TestShopDeliverySettingView(APITestCase):
    """ Тестирование API для управления настройками доставки магазина.

        Проверяются:
        - получение списка выбранных магазином тарифов CDEK;
        - сохранение выбранных тарифов магазина;
        - удаление всех настроек доставки магазина.

        В тестах используются mock-объекты для проверки прав доступа,
        получения магазина пользователя и списка доступных тарифов,
        что позволяет тестировать только логику работы представления. """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.shop = Shop.objects.create(
            owner=self.user,
            name="Shop",
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

    @patch(
        "users.permissions.IsCustomAuthenticated.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "seller.views.ShopDeliverySettingViewSet.get_user_shop"
    )
    def test_list(
        self,
        mocked_shop,
        *_,
    ):
        """  Проверяет получение списка тарифов доставки, настроенных для магазина.

            Тест создает связь между магазином и тарифом CDEK, выполняет GET-запрос
            к эндпоинту получения настроек доставки и проверяет, что запрос
            успешно обработан и возвращает HTTP 200 OK. """

        mocked_shop.return_value = self.shop

        ShopDeliverySetting.objects.create(
            shop=self.shop,
            tariff=self.tariff,
        )

        response = self.client.get(
            f"/api/shops/{self.shop.id}/delivery-settings/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    @patch(
        "users.permissions.IsCustomAuthenticated.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "seller.services.ShopDeliverySettingService.get_available_tariff_codes"
    )
    @patch(
        "seller.views.ShopDeliverySettingViewSet.get_user_shop"
    )
    def test_create(
        self,
        mocked_shop,
        mocked_codes,
        *_,
    ):
        """ Проверяет сохранение тарифов доставки для магазина.

            Тест подменяет получение доступных тарифов и магазина, отправляет
            POST-запрос с кодом тарифа и проверяет, что настройки доставки
            успешно сохраняются, а сервер возвращает HTTP 204 No Content. """

        mocked_shop.return_value = self.shop
        mocked_codes.return_value = {499}

        response = self.client.post(
            f"/api/shops/{self.shop.id}/delivery-settings/",
            {"tariffs": [499]},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

    @patch(
        "users.permissions.IsCustomAuthenticated.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "seller.views.ShopDeliverySettingViewSet.get_user_shop"
    )
    def test_delete(
        self,
        mocked_shop,
        *_,
    ):
        """ Проверяет удаление всех настроек доставки магазина.

            Тест предварительно создает настройку доставки, выполняет DELETE-запрос,
            затем проверяет, что сервер возвращает HTTP 204 No Content и все
            настройки доставки магазина удалены из базы данных. """

        mocked_shop.return_value = self.shop

        ShopDeliverySetting.objects.create(
            shop=self.shop,
            tariff=self.tariff,
        )

        response = self.client.delete(
            f"/api/shops/{self.shop.id}/delivery-settings/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertEqual(
            ShopDeliverySetting.objects.count(),
            0,
        )