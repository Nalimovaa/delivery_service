from django.db import models
from django.contrib.auth import get_user_model
from seller.models import Shop


User = get_user_model()


class Product(models.Model):
    """ Карточка товара (не уникальный товар, а его описание) """

    name = models.CharField(max_length=255)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="products")

    def __str__(self):
        return self.name


class UniqueProduct(models.Model):
    """ Конкретная продаваемая единица (вариант товара) (вариант товара, который может отличаться по цвету, размеру и т.д.)."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )
    ware_key = models.CharField(max_length=100, unique=True) # Артикул товара (уникальный идентификатор варианта товара, например, SKU)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Цена товара

    color = models.CharField(max_length=50) # Цвет товара (например, красный, синий, зеленый)
    size = models.CharField(max_length=20) # Размер товара (например, S, M, L, XL)
    height = models.PositiveIntegerField()  # высота (в сантиметрах)
    length = models.PositiveIntegerField()  # длина (в сантиметрах)
    width = models.PositiveIntegerField()  # ширина (в сантиметрах)
    weight = models.PositiveIntegerField()  # Вес (за единицу товара, в граммах)

    stock = models.PositiveIntegerField(default=0) # Текущее доступное количество конкретного варианта товара на складе продавца.

    def __str__(self):
        return (
            f"{self.product.name} "
            f"({self.color}, {self.size})"
        )