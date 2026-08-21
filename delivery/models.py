from django.db import models

from delivery.enums import DeliveryType
from delivery.managers import CDEKTariffManager, CDEKCityManager, CDEKDeliveryPointManager


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
        "seller.Shop",
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
        max_digits=12,
        decimal_places=3,
        verbose_name="Минимальный вес",
    )

    weight_max = models.DecimalField(
        max_digits=12,
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


class CDEKCity(models.Model):
    """Населенный пункт из справочника СДЭК."""

    code = models.IntegerField(
        unique=True,
        db_index=True,
        verbose_name="Код населенного пункта СДЭК",
    )

    city_uuid = models.UUIDField(
        unique=True,
        verbose_name="UUID населенного пункта СДЭК",
    )

    city = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Название населенного пункта",
    )

    fias_guid = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="UUID ФИАС населенного пункта",
    )

    country_code = models.CharField(
        max_length=2,
        db_index=True,
        verbose_name="Код страны",
    )

    country = models.CharField(
        max_length=255,
        verbose_name="Страна",
    )

    region = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Регион",
    )

    region_code = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Код региона СДЭК",
    )

    sub_region = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Район региона",
    )

    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Долгота",
    )

    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Широта",
    )

    time_zone = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Часовой пояс",
    )

    payment_limit = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Ограничение наложенного платежа",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    objects = CDEKCityManager()

    class Meta:
        verbose_name = "Населенный пункт CDEK"
        verbose_name_plural = "Населенные пункты CDEK"
        ordering = ["country_code", "region", "city"]
        indexes = [
            models.Index(
                fields=["city", "region", "sub_region"],
            ),
            models.Index(
                fields=["country_code", "region_code"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.city}, "
            f"{self.region}, "
            f"{self.country}"
        )



class CDEKDeliveryPoint(models.Model):
    """Пункт выдачи/приема CDEK."""

    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="Код ПВЗ CDEK",
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Название ПВЗ",
    )

    uuid = models.UUIDField(
        unique=True,
        verbose_name="UUID ПВЗ CDEK",
    )

    address_comment = models.TextField(
        null=True,
        blank=True,
        verbose_name="Комментарий к адресу",
    )

    nearest_station = models.TextField(
        null=True,
        blank=True,
        verbose_name="Ближайшая остановка",
    )

    nearest_metro_station = models.TextField(
        null=True,
        blank=True,
        verbose_name="Ближайшее метро",
    )

    work_time = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Время работы",
    )

    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name="Email",
    )

    note = models.TextField(
        null=True,
        blank=True,
        verbose_name="Примечание",
    )

    type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Тип пункта",
    )

    owner_code = models.CharField(
        max_length=50,
        verbose_name="Код владельца",
    )

    take_only = models.BooleanField(
        default=False,
        verbose_name="Только выдача",
    )

    is_handout = models.BooleanField(
        default=False,
        verbose_name="Выдача заказов",
    )

    is_reception = models.BooleanField(
        default=False,
        verbose_name="Прием заказов",
    )

    is_dressing_room = models.BooleanField(
        default=False,
        verbose_name="Есть примерочная",
    )

    is_ltl = models.BooleanField(
        default=False,
        verbose_name="Поддерживает LTL",
    )

    have_cashless = models.BooleanField(
        default=False,
        verbose_name="Безналичная оплата",
    )

    have_cash = models.BooleanField(
        default=False,
        verbose_name="Наличная оплата",
    )

    have_fast_payment_system = models.BooleanField(
        default=False,
        verbose_name="Система быстрых платежей",
    )

    allowed_cod = models.BooleanField(
        default=False,
        verbose_name="Разрешен наложенный платеж",
    )

    office_image_list = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Изображения ПВЗ",
    )

    work_time_list = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Расписание работы",
    )

    work_time_exception_list = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Исключения рабочего времени",
    )

    status = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Статус ПВЗ",
    )

    # Данные location из ответа CDEK
    country_code = models.CharField(
        max_length=2,
        db_index=True,
        verbose_name="Код страны",
    )

    region_code = models.IntegerField(
        db_index=True,
        verbose_name="Код региона CDEK",
    )

    region = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Регион",
    )

    city_code = models.IntegerField(
        db_index=True,
        verbose_name="Код города CDEK",
    )

    city = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Город",
    )

    postal_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Почтовый индекс",
    )

    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Долгота",
    )

    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Широта",
    )

    address = models.TextField(
        null=True,
        blank=True,
        verbose_name="Адрес",
    )

    address_full = models.TextField(
        null=True,
        blank=True,
        verbose_name="Полный адрес",
    )

    city_uuid = models.UUIDField(
        verbose_name="UUID города CDEK",
    )

    ltl_acceptance_partners = models.BooleanField(
        default=False,
        verbose_name="Прием LTL партнерами",
    )

    ltl_issuance_partners = models.BooleanField(
        default=False,
        verbose_name="Выдача LTL партнерами",
    )

    fulfillment = models.BooleanField(
        default=False,
        verbose_name="Fulfillment",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    objects = CDEKDeliveryPointManager()

    class Meta:
        verbose_name = "Пункт выдачи CDEK"
        verbose_name_plural = "Пункты выдачи CDEK"
        ordering = ["country_code", "region", "city", "name"]
        indexes = [
            models.Index(
                fields=["city", "region"],
            ),
            models.Index(
                fields=["country_code", "region_code"],
            ),
            models.Index(
                fields=["city_code"],
            ),
            models.Index(
                fields=["status", "is_active"],
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"