from django.db import models

from delivery.models import CDEKTariff
from users.models import User

class Shop(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shops")
    legal_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class ShopDeliverySetting(models.Model):
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="delivery_settings",
    )

    tariff = models.ForeignKey(
        CDEKTariff,
        on_delete=models.PROTECT,
        related_name="shop_settings",
    )

    is_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)