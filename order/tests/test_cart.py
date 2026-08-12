# docker exec -it delivery_service-web-1 python manage.py test order.tests.test_cart

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from order.models import Cart, CartItem
from product.models import Product, UniqueProduct
from seller.models import Shop


User = get_user_model()


class CartAPITestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@test.com",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            email="other_buyer@test.com",
            password="password123",
        )

        self.client.force_authenticate(
            user=self.user,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer test-token"
        )

        self.shop = Shop.objects.create(
            name="Test shop",
            owner=self.user,
            carrier=1,
        )

        self.product = Product.objects.create(
            name="Nike Air",
            shop=self.shop,
        )

        self.unique_product = UniqueProduct.objects.create(
            product=self.product,
            ware_key="SKU-001",
            price=Decimal("12000.00"),
            color="Белый",
            size="42",
            height=10,
            length=30,
            width=20,
            weight=800,
            stock=10,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_get_cart_creates_cart(self, *_):
        """Корзина создаётся лениво."""
        self.assertFalse(
            Cart.objects.filter(
                owner=self.user,
            ).exists()
        )

        response = self.client.get(
            "/api/cart/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        cart = Cart.objects.get(
            owner=self.user,
        )

        self.assertEqual(
            response.data["id"],
            cart.id,
        )

        self.assertEqual(
            response.data["owner"],
            self.user.id,
        )

        self.assertEqual(
            response.data["items"],
            [],
        )

        self.assertEqual(
            Decimal(response.data["items_total"]),
            Decimal("0"),
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_get_cart_does_not_create_second_cart(self, *_):
        """Повторный запрос корзины не создаёт вторую корзину."""
        response1 = self.client.get(
            "/api/cart/"
        )

        response2 = self.client.get(
            "/api/cart/"
        )

        self.assertEqual(
            response1.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response2.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response1.data["id"],
            response2.data["id"],
        )

        self.assertEqual(
            Cart.objects.filter(
                owner=self.user,
            ).count(),
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
    def test_add_item_to_cart(self, *_):
        """Добавление товара в корзину."""
        response = self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        cart = Cart.objects.get(
            owner=self.user,
        )

        cart_item = CartItem.objects.get(
            cart=cart,
            unique_product=self.unique_product,
        )

        self.assertEqual(
            cart_item.amount,
            2,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_cart_item_contains_current_price(self, *_):
        """Позиция корзины содержит актуальную цену UniqueProduct."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        response = self.client.get(
            "/api/cart/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item = response.data["items"][0]

        self.assertEqual(
            item["unique_product"],
            self.unique_product.id,
        )

        self.assertEqual(
            Decimal(item["price"]),
            Decimal("12000.00"),
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_cart_item_price_updates_with_unique_product_price(self, *_):
        """Цена в корзине берётся динамически из UniqueProduct."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        self.unique_product.price = Decimal("15000.00")
        self.unique_product.save(
            update_fields=("price",)
        )

        response = self.client.get(
            "/api/cart/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item = response.data["items"][0]

        self.assertEqual(
            Decimal(item["price"]),
            Decimal("15000.00"),
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_cart_contains_items_total(self, *_):
        """Корзина содержит общую стоимость товаров без доставки."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        response = self.client.get(
            "/api/cart/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Decimal(response.data["items_total"]),
            Decimal("24000.00"),
        )
    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_cart_items_total_updates_with_unique_product_price(self, *_):
        """Общая стоимость корзины пересчитывается при изменении цены."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        self.unique_product.price = Decimal("15000.00")
        self.unique_product.save(
            update_fields=("price",)
        )

        response = self.client.get(
            "/api/cart/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Decimal(response.data["items_total"]),
            Decimal("30000.00"),
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_add_item_creates_cart_if_not_exists(self, *_):
        """Добавление товара создаёт корзину, если её ещё нет."""
        self.assertFalse(
            Cart.objects.filter(
                owner=self.user,
            ).exists()
        )

        response = self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Cart.objects.filter(
                owner=self.user,
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
    def test_add_existing_item_increases_amount(self, *_):
        """Добавление существующего товара увеличивает количество."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        response = self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        cart = Cart.objects.get(
            owner=self.user,
        )

        self.assertEqual(
            CartItem.objects.filter(
                cart=cart,
                unique_product=self.unique_product,
            ).count(),
            1,
        )

        item = CartItem.objects.get(
            cart=cart,
            unique_product=self.unique_product,
        )

        self.assertEqual(
            item.amount,
            5,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_add_item_with_zero_amount(self, *_):
        """Количество 0 запрещено."""
        response = self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 0,
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
    def test_add_item_with_negative_amount(self, *_):
        """Отрицательное количество запрещено."""
        response = self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": -1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_add_nonexistent_product(self, *_):
        """Несуществующий вариант товара нельзя добавить."""
        response = self.client.post(
            "/api/cart/items/",
            {
                "unique_product": 999999,
                "amount": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "unique_product",
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
    def test_update_cart_item(self, *_):
        """Обновление количества товара в корзине."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        item = CartItem.objects.get(
            cart__owner=self.user,
            unique_product=self.unique_product,
        )

        response = self.client.patch(
            f"/api/cart/items/{item.id}/",
            {
                "amount": 7,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.amount,
            7,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_update_cart_item_with_zero_amount(self, *_):
        """Количество товара нельзя обновить на 0."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        item = CartItem.objects.get(
            cart__owner=self.user,
        )

        response = self.client.patch(
            f"/api/cart/items/{item.id}/",
            {
                "amount": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_delete_cart_item(self, *_):
        """Удаление товара из корзины."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        item = CartItem.objects.get(
            cart__owner=self.user,
        )

        response = self.client.delete(
            f"/api/cart/items/{item.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            CartItem.objects.filter(
                id=item.id,
            ).exists()
        )

        self.assertTrue(
            Cart.objects.filter(
                owner=self.user,
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
    def test_clear_cart(self, *_):
        """Очистка корзины пользователя."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 3,
            },
            format="json",
        )

        cart = Cart.objects.get(
            owner=self.user,
        )

        response = self.client.delete(
            "/api/cart/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        cart.refresh_from_db()

        self.assertEqual(
            cart.items.count(),
            0,
        )

        self.assertTrue(
            Cart.objects.filter(
                id=cart.id,
                owner=self.user,
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
    def test_user_cannot_modify_another_user_cart_item(self, *_):
        """Пользователь не может изменять товары в чужой корзине."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        item = CartItem.objects.get(
            cart__owner=self.user,
        )

        self.client.force_authenticate(
            user=self.other_user,
        )

        response = self.client.patch(
            f"/api/cart/items/{item.id}/",
            {
                "amount": 100,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.amount,
            2,
        )

    @patch(
        "users.permissions.RolePermission.has_permission",
        return_value=True,
    )
    @patch(
        "users.permissions.RolePermission.has_object_permission",
        return_value=True,
    )
    def test_user_cannot_delete_another_user_cart_item(self, *_):
        """Пользователь не может удалять товары в чужой корзине."""
        self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 2,
            },
            format="json",
        )

        item = CartItem.objects.get(
            cart__owner=self.user,
        )

        self.client.force_authenticate(
            user=self.other_user,
        )

        response = self.client.delete(
            f"/api/cart/items/{item.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            CartItem.objects.filter(
                id=item.id,
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
    def test_add_to_cart_does_not_change_stock(self, *_):
        """Добавление товара в корзину не изменяет остаток."""
        initial_stock = self.unique_product.stock

        response = self.client.post(
            "/api/cart/items/",
            {
                "unique_product": self.unique_product.id,
                "amount": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            initial_stock,
        )

    def test_get_cart_requires_authentication(self):
        """Получение корзины требует аутентификации."""
        self.client.force_authenticate(
            user=None,
        )

        response = self.client.get(
            "/api/cart/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )