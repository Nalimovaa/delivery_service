""" docker exec -it delivery_service-web-1 python manage.py test seller.tests.test_views """

from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import CDEKTariff, DeliveryType
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

        self.client.force_authenticate(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer test-token"
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

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
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
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
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
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
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


class TestShopViewSet(APITestCase):
    """
    Тестирование API управления магазинами.

    Проверяются:
    - создание магазина;
    - получение списка магазинов;
    - получение магазина по ID;
    - изменение службы доставки;
    - удаление магазина.

    В тестах DeliveryFactory заменяется mock-объектом,
    так как проверяется только взаимодействие ViewSet
    с фабрикой, а не сама логика служб доставки.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.client.force_authenticate(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer test-token"
        )

        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test shop",
            carrier=DeliveryType.CDEK,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    @patch(
        "seller.views.DeliveryFactory.initialize",
    )
    def test_create_shop_with_delivery_initialize(
        self,
        mocked_initialize,
        *_,
    ):
        """
        Проверяет создание магазина.

        После создания магазина должна быть вызвана
        DeliveryFactory.initialize().
        """

        response = self.client.post(
            "/api/shops/",
            {
                "name": "New shop",
                "carrier": DeliveryType.CDEK,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        mocked_initialize.assert_called_once()

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_list_shops(
        self,
        *_,
    ):
        """
        Проверяет получение списка магазинов.
        """

        response = self.client.get(
            "/api/shops/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_retrieve_shop(
        self,
        *_,
    ):
        """
        Проверяет получение магазина по ID.
        """

        response = self.client.get(
            f"/api/shops/{self.shop.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    @patch(
        "seller.views.DeliveryFactory.initialize",
    )
    @patch(
        "seller.views.DeliveryFactory.cleanup",
    )
    def test_update_shop_carrier(
        self,
        mocked_cleanup,
        mocked_initialize,
        *_,
    ):
        """
        Проверяет изменение службы доставки.

        Если carrier изменился:
        - вызывается cleanup старой службы;
        - вызывается initialize новой службы.
        """

        response = self.client.patch(
            f"/api/shops/{self.shop.id}/",
            {
                "carrier": DeliveryType.BOXBERRY,
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mocked_cleanup.assert_called_once()

        mocked_initialize.assert_called_once()

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    @patch(
        "seller.views.DeliveryFactory.cleanup",
    )
    def test_delete_shop(
        self,
        mocked_cleanup,
        *_,
    ):
        """
        Проверяет удаление магазина.

        Перед удалением должна вызываться
        DeliveryFactory.cleanup().
        """

        response = self.client.delete(
            f"/api/shops/{self.shop.id}/",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Shop.objects.filter(
                id=self.shop.id
            ).exists()
        )


        mocked_cleanup.assert_called_once()