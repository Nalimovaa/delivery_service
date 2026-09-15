from django.db import models
from django.contrib.auth import get_user_model
from delivery.models import OrderDelivery
from order.enams import OrderStatus, ReturnRequestStatus
from product.models import UniqueProduct

User = get_user_model()

class Order(models.Model):
    """ Заказ пользователя (пользователь нажал кнопку "Оформить заказ") """

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders") # Покупатель
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(
        choices=OrderStatus.choices,
        default=OrderStatus.PROCESSING,
    )

    def __str__(self):
        return (
            f"Order #{self.pk} "
            f"({self.created_at:%Y-%m-%d %H:%M})"
        )


class OrderProduct(models.Model):
    """ Строка заказа (конкретный товар в заказе, с указанием количества) """

    # Связь с заказом, к которому относится данная строка заказа
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # Связь с отправлением, к которому относится данная строка заказа (может быть null, если заказ еще не распределен по отправлениям)
    order_delivery = models.ForeignKey(
        OrderDelivery,
        on_delete=models.PROTECT,
        related_name="items",
        null=True,
        blank=True,
    )

    unique_product = models.ForeignKey( # вариант товара
        UniqueProduct,
        on_delete=models.PROTECT,
        related_name="order_items"
    )
    # информация о товаре в тсроке заказа
    amount = models.PositiveIntegerField() # Количество единиц вариант товара в строке заказа
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Цена товара на момент оформления заказа
    product_name = models.CharField(max_length=255) # Название товара на момент оформления заказа

    def __str__(self):
        return (
            f"{self.unique_product} × {self.amount}"
        )


class Cart(models.Model):
    """ Корзина пользователя (пользователь добавил товары в корзину, но еще не оформил заказ) """
    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CartItem(models.Model):
    """ Строка корзины (конкретный товар в корзине, с указанием количества) """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    unique_product = models.ForeignKey(
        UniqueProduct,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    amount = models.PositiveIntegerField()

    class Meta:
        """Один вариант товара может присутствовать в корзине только один раз, а количество хранится в amount."""
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "unique_product"],
                name="unique_product_in_cart",
            ),
        ]


class ReturnRequest(models.Model):
    """
    Заявка покупателя на возврат полученного заказа.
    """

    order_delivery = models.ForeignKey(
        OrderDelivery,
        on_delete=models.PROTECT,
        related_name="return_requests",
        verbose_name="Доставка заказа",
    )

    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="return_requests", verbose_name="Покупатель")

    status = models.PositiveSmallIntegerField(
        choices=ReturnRequestStatus.choices,
        default=ReturnRequestStatus.REQUESTED,
        verbose_name="Статус заявки",
    )

    reason = models.TextField(
        verbose_name="Причина возврата",
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Причина отказа",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    @property
    def shop(self):
        return self.order_delivery.shop

    @property
    def seller(self):
        return self.shop.owner

    def __str__(self):
        return (
            f"Заявка на возврат #{self.id} "
            f"от {self.owner.email}"
        )