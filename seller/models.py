from django.db import models
from django.conf import settings
from delivery.models import DeliveryType
from users.models import User



class Shop(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shops")
    legal_info = models.TextField(blank=True, null=True)
    location_from = models.CharField(max_length=255, blank=True, null=True) # город отправления магазина
    carrier = models.IntegerField(choices=DeliveryType.choices) # транспортная компания


    def __str__(self):
        return self.name


class ShopDeliverySetting(models.Model):
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="delivery_settings",
    )

    tariff = models.ForeignKey(
        "delivery.CDEKTariff",
        on_delete=models.PROTECT,
        related_name="shop_settings",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [ # чтобы нельзя было выбрать один и тот же тариф несколько раз
            models.UniqueConstraint(
                fields=("shop", "tariff"),
                name="unique_shop_tariff",
            )
        ]


class SellerRequestStatus(models.TextChoices):
    PENDING = "pending", "На рассмотрении"
    APPROVED = "approved", "Одобрена"
    REJECTED = "rejected", "Отклонена"

class SellerRequest(models.Model):
    """Форма заявки на получение роли Seller"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_requests", )

    status = models.CharField(
        max_length=20,
        choices=SellerRequestStatus.choices,
        default=SellerRequestStatus.PENDING, )

    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Причина отказа", )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, )

    def __str__(self):
        return f"Заявка #{self.id}, email: {self.user.email},  status: {self.status}"