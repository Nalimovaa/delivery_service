# docker exec -it delivery_service-web-1 python manage.py test product.tests.test_views

from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from delivery.enums import DeliveryType
from product.models import Product, UniqueProduct
from seller.models import Shop
from users.models import User, Role


class TestProductViewSet(APITestCase):
    """
    Тестирование API ProductViewSet.

    Проверяется:
    - создание товара в своем магазине;
    - запрет создания товара в чужом магазине;
    - получение списка товаров;
    - получение товара по ID.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.other_user = User.objects.create(
            email="other@test.com",
        )

        self.client.force_authenticate(
            user=self.user,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer test-token"
        )

        self.shop = Shop.objects.create(
            owner=self.user,
            name="My shop",
            carrier=DeliveryType.CDEK,
        )

        self.other_shop = Shop.objects.create(
            owner=self.other_user,
            name="Other shop",
            carrier=DeliveryType.CDEK,
        )

        self.product = Product.objects.create(
            name="Existing product",
            shop=self.shop,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_create_product(
        self,
        *_,
    ):
        """Создание товара в собственном магазине."""

        response = self.client.post(
            "/api/products/",
            {
                "name": "New product",
                "shop": self.shop.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        product = Product.objects.get(
            name="New product",
        )

        self.assertEqual(
            product.shop,
            self.shop,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_create_product_in_foreign_shop(
        self,
        *_,
    ):
        """Нельзя создать товар в чужом магазине."""

        response = self.client.post(
            "/api/products/",
            {
                "name": "Forbidden product",
                "shop": self.other_shop.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "shop",
            response.data,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_list_products(
        self,
        *_,
    ):
        """Получение списка товаров."""

        response = self.client.get(
            "/api/products/",
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
    def test_retrieve_product(
        self,
        *_,
    ):
        """Получение товара по ID."""

        response = self.client.get(
            f"/api/products/{self.product.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.product.id,
        )


class TestUniqueProductViewSet(APITestCase):
    """
    Тестирование API UniqueProductViewSet.

    Проверяется:
    - создание варианта товара;
    - запрет создания варианта чужого товара;
    - получение списка;
    - получение конкретного варианта;
    - изменение;
    - частичное изменение;
    - удаление;
    - пополнение склада;
    - списание со склада.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.other_user = User.objects.create(
            email="other@test.com",
        )

        self.client.force_authenticate(
            user=self.user,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer test-token"
        )

        self.shop = Shop.objects.create(
            owner=self.user,
            name="My shop",
            carrier=DeliveryType.CDEK,
        )

        self.other_shop = Shop.objects.create(
            owner=self.other_user,
            name="Other shop",
            carrier=DeliveryType.CDEK,
        )

        self.product = Product.objects.create(
            name="My product",
            shop=self.shop,
        )

        self.other_product = Product.objects.create(
            name="Other product",
            shop=self.other_shop,
        )

        self.unique_product = UniqueProduct.objects.create(
            product=self.product,
            ware_key="SKU-001",
            price=Decimal("1000.00"),
            color="Красный",
            size="L",
            height=20,
            length=30,
            width=10,
            weight=500,
            stock=10,
        )

    def get_unique_product_data(self):
        return {
            "product": self.product.id,
            "ware_key": "SKU-002",
            "price": "1500.00",
            "color": "Синий",
            "size": "M",
            "height": 25,
            "length": 35,
            "width": 15,
            "weight": 600,
        }

    def permission_patches(self):
        return (
            patch(
                "users.permissions.RolePermission.has_permission",
                return_value=True,
            ),
            patch(
                "users.permissions.RolePermission.has_object_permission",
                return_value=True,
            ),
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_create_unique_product(
        self,
        *_,
    ):
        """Создание варианта своего товара."""

        response = self.client.post(
            "/api/unique-products/",
            self.get_unique_product_data(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        unique_product = UniqueProduct.objects.get(
            ware_key="SKU-002",
        )

        self.assertEqual(
            unique_product.product,
            self.product,
        )

        self.assertEqual(
            unique_product.stock,
            0,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_create_unique_product_in_foreign_product(
        self,
        *_,
    ):
        """Нельзя создать вариант чужого товара."""

        data = self.get_unique_product_data()
        data["product"] = self.other_product.id

        response = self.client.post(
            "/api/unique-products/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "product",
            response.data,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_list_unique_products(
        self,
        *_,
    ):
        """Получение списка вариантов."""

        response = self.client.get(
            "/api/unique-products/",
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
    def test_retrieve_unique_product(
        self,
        *_,
    ):
        """Получение варианта товара."""

        response = self.client.get(
            f"/api/unique-products/{self.unique_product.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.unique_product.id,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_update_unique_product(
        self,
        *_,
    ):
        """Полное изменение варианта товара."""

        data = self.get_unique_product_data()
        data["ware_key"] = "SKU-001"
        data["color"] = "Зеленый"

        response = self.client.put(
            f"/api/unique-products/{self.unique_product.id}/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.color,
            "Зеленый",
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_partial_update_unique_product(
        self,
        *_,
    ):
        """Частичное изменение варианта товара."""

        response = self.client.patch(
            f"/api/unique-products/{self.unique_product.id}/",
            {
                "price": "2000.00",
                "color": "Черный",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.price,
            Decimal("2000.00"),
        )

        self.assertEqual(
            self.unique_product.color,
            "Черный",
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_stock_is_not_updated_directly(
        self,
        *_,
    ):
        """
        Поле stock read_only и не должно изменяться
        через обычный PATCH.
        """

        response = self.client.patch(
            f"/api/unique-products/{self.unique_product.id}/",
            {
                "stock": 100,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_delete_unique_product(
        self,
        *_,
    ):
        """Удаление варианта товара."""

        unique_product_id = self.unique_product.id

        response = self.client.delete(
            f"/api/unique-products/{unique_product_id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            UniqueProduct.objects.filter(
                id=unique_product_id,
            ).exists()
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_increase_stock(
        self,
        *_,
    ):
        """Пополнение склада."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/increase/",
            {
                "amount": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            15,
        )

        self.assertEqual(
            response.data["stock"],
            15,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_increase_stock_without_amount(
        self,
        *_,
    ):
        """Пополнение без указания количества запрещено."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/increase/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "amount",
            response.data,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_increase_stock_with_invalid_amount(
        self,
        *_,
    ):
        """Пополнение некорректным количеством запрещено."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/increase/",
            {
                "amount": "abc",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "amount",
            response.data,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_increase_stock_with_zero_amount(
        self,
        *_,
    ):
        """Пополнение нулевым количеством запрещено."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/increase/",
            {
                "amount": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_decrease_stock(
        self,
        *_,
    ):
        """Списание товара со склада."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/decrease/",
            {
                "amount": 4,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            6,
        )

        self.assertEqual(
            response.data["stock"],
            6,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_decrease_stock_when_not_enough(
        self,
        *_,
    ):
        """Нельзя списать больше товара, чем есть на складе."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/decrease/",
            {
                "amount": 11,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["amount"],
            "Недостаточно товара на складе.",
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_decrease_stock_without_amount(
        self,
        *_,
    ):
        """Списание без количества запрещено."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/decrease/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "amount",
            response.data,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_decrease_stock_with_invalid_amount(
        self,
        *_,
    ):
        """Списание некорректным количеством запрещено."""

        response = self.client.post(
            f"/api/unique-products/{self.unique_product.id}/stock/decrease/",
            {
                "amount": "abc",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "amount",
            response.data,
        )