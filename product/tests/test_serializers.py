# docker exec -it delivery_service-web-1 python manage.py test product.tests.test_serializers

from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from delivery.enums import DeliveryType
from product.models import Product, UniqueProduct
from product.serializers import (
    ProductSerializer,
    UniqueProductSerializer,
    StockAmountSerializer,
)
from seller.models import Shop
from users.models import User
from django.contrib.auth.models import AnonymousUser


class TestProductSerializer(TestCase):
    """
    Тестирование ProductSerializer.

    Проверяется:
    - создание товара в своем магазине;
    - запрет создания товара в чужом магазине;
    - запрет работы без авторизованного пользователя.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.other_user = User.objects.create(
            email="other@test.com",
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

        self.factory = APIRequestFactory()

    def test_validate_shop_owner(self):
        """Пользователь может создать товар в своем магазине."""

        request = self.factory.post("/api/products/")
        request.user = self.user

        serializer = ProductSerializer(
            data={
                "name": "Test product",
                "shop": self.shop.id,
            },
            context={"request": request},
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_validate_foreign_shop(self):
        """Нельзя создать товар в чужом магазине."""

        request = self.factory.post("/api/products/")
        request.user = self.user

        serializer = ProductSerializer(
            data={
                "name": "Test product",
                "shop": self.other_shop.id,
            },
            context={"request": request},
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assertIn(
            "shop",
            serializer.errors,
        )

        self.assertEqual(
            str(serializer.errors["shop"][0]),
            "Вы можете создавать товары только в своих магазинах.",
        )

    def test_validate_shop_without_authenticated_user(self):
        """Без авторизованного пользователя создание товара запрещено."""

        request = self.factory.post("/api/products/")
        request.user = AnonymousUser()

        serializer = ProductSerializer(
            data={
                "name": "Test product",
                "shop": self.shop.id,
            },
            context={"request": request},
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assertIn(
            "shop",
            serializer.errors,
        )

        self.assertEqual(
            str(serializer.errors["shop"][0]),
            "Пользователь не авторизован.",
        )


class TestUniqueProductSerializer(TestCase):
    """
    Тестирование UniqueProductSerializer.

    Проверяется:
    - создание варианта своего товара;
    - запрет добавления варианта в чужой товар;
    - stock является read-only.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.other_user = User.objects.create(
            email="other@test.com",
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

        self.factory = APIRequestFactory()

    def get_data(self, product):
        return {
            "product": product.id,
            "ware_key": "SKU-001",
            "price": "1000.00",
            "color": "Красный",
            "size": "L",
            "height": 20,
            "length": 30,
            "width": 10,
            "weight": 500,
            "stock": 100,
        }

    def test_validate_product_owner(self):
        """Пользователь может создать вариант своего товара."""

        request = self.factory.post("/api/unique-products/")
        request.user = self.user

        serializer = UniqueProductSerializer(
            data=self.get_data(self.product),
            context={"request": request},
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_validate_foreign_product(self):
        """Нельзя добавить вариант в чужой товар."""

        request = self.factory.post("/api/unique-products/")
        request.user = self.user

        serializer = UniqueProductSerializer(
            data=self.get_data(self.other_product),
            context={"request": request},
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assertIn(
            "product",
            serializer.errors,
        )

        self.assertEqual(
            str(serializer.errors["product"][0]),
            "Вы можете добавлять варианты только в свои товары.",
        )

    def test_stock_is_read_only(self):
        """Поле stock нельзя изменить через сериалайзер."""

        request = self.factory.post("/api/unique-products/")
        request.user = self.user

        serializer = UniqueProductSerializer(
            data=self.get_data(self.product),
            context={"request": request},
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

        self.assertNotIn(
            "stock",
            serializer.validated_data,
        )


class TestStockAmountSerializer(TestCase):

    def test_valid_amount(self):
        """Положительное количество является валидным."""

        serializer = StockAmountSerializer(
            data={"amount": 5},
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_zero_amount(self):
        """Нулевое количество запрещено."""

        serializer = StockAmountSerializer(
            data={"amount": 0},
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assertIn(
            "amount",
            serializer.errors,
        )

    def test_negative_amount(self):
        """Отрицательное количество запрещено."""

        serializer = StockAmountSerializer(
            data={"amount": -5},
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assertIn(
            "amount",
            serializer.errors,
        )

    def test_missing_amount(self):
        """Количество обязательно."""

        serializer = StockAmountSerializer(
            data={},
        )

        self.assertFalse(
            serializer.is_valid(),
        )

        self.assertIn(
            "amount",
            serializer.errors,
        )
