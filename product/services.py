from django.db import transaction

from order.models import Cart, CartItem
from product.models import UniqueProduct


class StockService:

    @staticmethod
    def get_stock(unique_product: UniqueProduct) -> int:
        """
        Возвращает текущий остаток товара.
        """
        return unique_product.stock

    @staticmethod
    @transaction.atomic
    def increase(
        unique_product: UniqueProduct,
        amount: int,
    ) -> UniqueProduct:
        """
        Увеличивает остаток товара на складе.
        """

        if amount <= 0:
            raise ValueError(
                "Количество для увеличения должно быть больше нуля."
            )

        unique_product.stock += amount
        unique_product.save(
            update_fields=["stock"],
        )

        return unique_product

    @staticmethod
    @transaction.atomic
    def decrease(
        unique_product: UniqueProduct,
        amount: int,
    ) -> UniqueProduct:
        """
        Уменьшает остаток товара на складе.
        """

        if amount <= 0:
            raise ValueError(
                "Количество для уменьшения должно быть больше нуля."
            )

        if unique_product.stock < amount:
            raise ValueError(
                "Недостаточно товара на складе."
            )

        unique_product.stock -= amount
        unique_product.save(
            update_fields=["stock"],
        )

        return unique_product

    @staticmethod
    def has_stock(
        unique_product: UniqueProduct,
        amount: int = 1,
    ) -> bool:
        """
        Проверяет наличие необходимого количества товара.
        """

        if amount <= 0:
            return False

        return unique_product.stock >= amount

    @staticmethod
    @transaction.atomic
    def reserve(
            unique_product_id: int,
            amount: int,
    ) -> UniqueProduct:
        """
        Резервирует товар на складе для заказа.
        """

        if amount <= 0:
            raise ValueError(
                "Количество должно быть больше нуля."
            )

        unique_product = (
            UniqueProduct.objects
            .select_for_update()
            .get(id=unique_product_id)
        )

        if unique_product.stock < amount:
            raise ValueError(
                "Недостаточно товара на складе."
            )

        unique_product.stock -= amount

        unique_product.save(
            update_fields=["stock"],
        )

        return unique_product


class CartService:
    """Данный сервис предназначен для управления корзиной пользователя, включая добавление,
    обновление и удаление товаров, а также очистку корзины."""

    @staticmethod
    def get_or_create_cart(user):
        """Получает корзину пользователя или создает новую, если она не существует."""
        cart, _ = Cart.objects.get_or_create(
            owner=user,
        )
        return cart

    @staticmethod
    @transaction.atomic
    def add_item(
        user,
        unique_product,
        amount,
    ):
        """Добавляет товар в корзину пользователя. Если товар уже существует в корзине, увеличивает его количество."""
        cart = CartService.get_or_create_cart(user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            unique_product=unique_product,
            defaults={
                "amount": amount,
            },
        )

        if not created:
            cart_item.amount += amount
            cart_item.save(
                update_fields=["amount"],
            )

        return cart_item

    @staticmethod
    @transaction.atomic
    def update_item(
        user,
        cart_item,
        amount,
    ):
        """Обновляет количество товара в корзине пользователя.
        Проверяет, что товар принадлежит корзине пользователя."""
        cart = CartService.get_or_create_cart(user)

        if cart_item.cart_id != cart.id:
            raise PermissionError(
                "Товар не принадлежит корзине пользователя."
            )

        cart_item.amount = amount
        cart_item.save(
            update_fields=["amount"],
        )

        return cart_item

    @staticmethod
    @transaction.atomic
    def remove_item(user, cart_item):
        """Удаляет товар из корзины пользователя.
        Проверяет, что товар принадлежит корзине пользователя."""
        cart = CartService.get_or_create_cart(user)

        if cart_item.cart_id != cart.id:
            raise PermissionError(
                "Товар не принадлежит корзине пользователя."
            )

        cart_item.delete()

    @staticmethod
    @transaction.atomic
    def clear(user):
        """Очищает корзину пользователя, удаляя все товары из нее."""
        cart = CartService.get_or_create_cart(user)
        cart.items.all().delete()