from django.db import models
from django.contrib.auth import get_user_model

from delivery.models import OrderDelivery
from product.models import Product, UniqueProduct

User = get_user_model()

class Order(models.Model):
    """ Заказ пользователя (пользователь нажал кнопку "Оформить заказ") """

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders") # Покупатель
    created_at = models.DateTimeField(auto_now_add=True)

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