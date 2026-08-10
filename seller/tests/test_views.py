""" docker exec -it delivery_service-web-1 python manage.py test seller.tests.test_views """

from decimal import Decimal
from unittest.mock import patch, ANY

from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import CDEKTariff, DeliveryType
from seller.models import Shop, ShopDeliverySetting
from users.models import User, Role, UserRole
from django.test import TestCase




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


from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import DeliveryType
from seller.models import Shop
from users.models import User, Role, UserRole


class TestShopViewSet(APITestCase):
    """
    Тестирование API управления магазинами.

    Проверяются:
    - создание магазина;
    - автоматическое назначение роли Seller;
    - получение списка магазинов;
    - получение магазина по ID;
    - изменение службы доставки;
    - удаление магазина;
    - сохранение роли Seller, если у пользователя остались магазины;
    - удаление роли Seller, если магазинов больше нет.

    DeliveryFactory и SellerService заменяются mock-объектами,
    так как логика этих сервисов тестируется отдельно.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.client.force_authenticate(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer test-token"
        )

        self.seller_role = Role.objects.create(
            name="Seller",
            description="Access to own store, products, orders and delivery settings",
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
    @patch(
        "seller.views.SellerService.assign_role",
    )
    def test_create_shop_with_seller_role_and_delivery_initialize(
        self,
        mocked_assign_role,
        mocked_initialize,
        *_,
    ):
        """
        После создания магазина:

        - магазин создаётся с текущим пользователем в owner;
        - вызывается SellerService.assign_role();
        - вызывается DeliveryFactory.initialize().
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

        shop = Shop.objects.get(
            name="New shop",
        )

        self.assertEqual(
            shop.owner,
            self.user,
        )

        mocked_assign_role.assert_called_once_with(
            self.user,
        )

        mocked_initialize.assert_called_once_with(
            shop,
        )

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
        При изменении службы доставки:

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
        "seller.views.SellerService.remove_role_if_no_shops",
    )
    @patch(
        "seller.views.DeliveryFactory.cleanup",
    )
    def test_delete_shop_keeps_seller_role_if_user_has_other_shops(
            self,
            mocked_cleanup,
            mocked_remove_role,
            *_,
    ):
        """
        Если у пользователя остаётся другой магазин:

        - удаляется только выбранный магазин;
        - другой магазин остаётся;
        - вызывается SellerService.remove_role_if_no_shops().
        """

        shop_id = self.shop.id
        shop_name = self.shop.name

        second_shop = Shop.objects.create(
            owner=self.user,
            name="Second shop",
            carrier=DeliveryType.CDEK,
        )

        response = self.client.delete(
            f"/api/shops/{shop_id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # Первый магазин удалён.
        self.assertFalse(
            Shop.objects.filter(
                id=shop_id,
            ).exists()
        )

        # Второй магазин остался.
        self.assertTrue(
            Shop.objects.filter(
                id=second_shop.id,
            ).exists()
        )

        # Проверяем, что cleanup вызван один раз.
        mocked_cleanup.assert_called_once_with(
            ANY,
        )

        cleanup_shop = mocked_cleanup.call_args.args[0]

        # После shop.delete() id становится None,
        # поэтому проверяем стабильное поле.
        self.assertEqual(
            cleanup_shop.name,
            shop_name,
        )

        # SellerService вызывается для владельца.
        mocked_remove_role.assert_called_once_with(
            self.user,
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
        "seller.views.SellerService.remove_role_if_no_shops",
    )
    @patch(
        "seller.views.DeliveryFactory.cleanup",
    )
    def test_delete_shop_with_seller_service(
            self,
            mocked_cleanup,
            mocked_remove_role,
            *_,
    ):
        """
        При удалении магазина:

        - вызывается DeliveryFactory.cleanup() с удаляемым магазином;
        - вызывается SellerService.remove_role_if_no_shops()
          для владельца магазина;
        - магазин удаляется.
        """

        shop_id = self.shop.id
        shop_name = self.shop.name

        response = self.client.delete(
            f"/api/shops/{shop_id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # Магазин действительно удалён.
        self.assertFalse(
            Shop.objects.filter(
                id=shop_id,
            ).exists()
        )

        # Проверяем, что cleanup был вызван один раз.
        mocked_cleanup.assert_called_once_with(
            ANY,
        )

        # Получаем объект, который был передан в cleanup.
        cleanup_shop = mocked_cleanup.call_args.args[0]

        # После shop.delete() его pk становится None,
        # поэтому проверяем стабильное поле.
        self.assertEqual(
            cleanup_shop.name,
            shop_name,
        )

        # Проверяем вызов SellerService.
        mocked_remove_role.assert_called_once_with(
            self.user,
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
        "seller.views.SellerService.remove_role_if_no_shops",
    )
    @patch(
        "seller.views.DeliveryFactory.cleanup",
    )
    def test_delete_shop_with_other_shops(
            self,
            mocked_cleanup,
            mocked_remove_role,
            *_,
    ):
        """
        Если у пользователя остаётся другой магазин:

        - удаляется только выбранный магазин;
        - другой магазин остаётся;
        - вызывается SellerService.remove_role_if_no_shops().
        """

        shop_id = self.shop.id
        shop_name = self.shop.name

        second_shop = Shop.objects.create(
            owner=self.user,
            name="Second shop",
            carrier=DeliveryType.CDEK,
        )

        response = self.client.delete(
            f"/api/shops/{shop_id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # Первый магазин удалён.
        self.assertFalse(
            Shop.objects.filter(
                id=shop_id,
            ).exists()
        )

        # Второй магазин остался.
        self.assertTrue(
            Shop.objects.filter(
                id=second_shop.id,
            ).exists()
        )

        mocked_cleanup.assert_called_once_with(
            ANY,
        )

        cleanup_shop = mocked_cleanup.call_args.args[0]

        self.assertEqual(
            cleanup_shop.name,
            shop_name,
        )

        mocked_remove_role.assert_called_once_with(
            self.user,
        )

