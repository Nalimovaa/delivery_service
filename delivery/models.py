from django.db import models

from delivery.managers import CDEKTariffManager
from seller.models import Shop


class DeliveryType(models.IntegerChoices):
    CDEK = 1, "СДЭК"
    # Добавьте другие типы доставки по мере необходимости:
    # BOXBERRY = 2, "Boxberry"
    # POST = 3, "Почта России"


class OrderDelivery(models.Model):
    """ Модель представляет отправку, сгруппированную по продавцу"""

    # Связь с заказом, к которому относится данная отправка.
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    # Связь с магазином, который осуществляет доставку. Это позволяет отслеживать, какой магазин отвечает за конкретную отправку.
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="deliveries",
    )
    # Тип доставки, используемый для данной отправки.
    delivery_type = models.PositiveSmallIntegerField(
        choices=DeliveryType.choices,
    )

    created_at = models.DateTimeField(auto_now_add=True)


class CdekDelivery(models.Model):
    """ Модель, представляющая метаданные о доставке для отправлений CDEK.
    Этот класс содержит информацию, связанную с доставкой заказа через службу CDEK,
    включая данные отслеживания и информацию о стоимости. """

    # Связь с моделью DeliveryMeta, которая содержит общую информацию о доставке.
    order_delivery = models.OneToOneField(
        OrderDelivery,
        on_delete=models.CASCADE,
        related_name="cdek",
    )

    # информация для создания заказа в системе CDEK
    cdek_office_code_from = models.CharField(max_length=255, blank=True,
                                             null=True)  # Код офиса, из которого отправляется груз
    cdek_office_code_to = models.CharField(max_length=255, blank=True,
                                           null=True)  # Код офиса, в который отправляется груз
    tariff_code = models.IntegerField(blank=True, null=True)  # Код тарифа, используемого для доставки

    # Уникальный идентификатор, присваиваемый до валидации заказа в системе CDEK. Этот идентификатор используется
    # для отслеживания заказа до его окончательного подтверждения.
    cdek_uuid = models.CharField(max_length=36, unique=True, null=True, blank=True)  # Уникальный идентификатор груза

    preliminary_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True,
                                            null=True)  # Предварительная стоимость доставки

    # Информация, присваиваемая после подтверждения заказа в системе CDEK.
    shipment_track_id = models.BigIntegerField(blank=True, null=True) # Идентификационный номер отслеживания посылки
    shipment_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # Стоимость доставки

    order_status = models.CharField(max_length=255, blank=True, null=True) # Статус заказа

    def __str__(self):
        return (
            f"CDEK #{self.shipment_track_id or '—'} "
            f"({self.order_status or '—'})"
        )


class CDEKTariff(models.Model):
    """
    Модель для хранения тарифов CDEK, доступных по договору.

    Источник данных:
    Модуль «Расчет стоимости доставки» → метод «Список доступных тарифов».
    """
    objects = CDEKTariffManager()  # подключение менеджера модели для работы с тарифами CDEK

    tariff_code = models.PositiveIntegerField(
        unique=True,
        verbose_name="Код тарифа",
    )

    tariff_name = models.CharField(
        max_length=255,
        verbose_name="Название тарифа",
    )

    delivery_mode = models.PositiveSmallIntegerField(
        verbose_name="Код режима доставки",
    )

    delivery_mode_name = models.CharField(
        max_length=50,
        verbose_name="Режим доставки",
    )

    weight_min = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        verbose_name="Минимальный вес",
    )

    weight_max = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        verbose_name="Максимальный вес",
    )

    length_max = models.PositiveIntegerField(
        verbose_name="Максимальная длина",
    )

    width_max = models.PositiveIntegerField(
        verbose_name="Максимальная ширина",
    )

    height_max = models.PositiveIntegerField(
        verbose_name="Максимальная высота",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    class Meta:
        verbose_name = "Тариф CDEK"
        verbose_name_plural = "Тарифы CDEK"
        ordering = ("tariff_name", "tariff_code")

    def __str__(self):
        return f"{self.tariff_name} ({self.tariff_code})"