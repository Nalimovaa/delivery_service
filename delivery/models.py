from django.db import models

from delivery.enums import DeliveryType, StockReservationStatus
from delivery.managers import CDEKTariffManager, CDEKCityManager, CDEKDeliveryPointManager
from order.enams import OrderDeliveryStatus


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

    status = models.PositiveSmallIntegerField(
        choices=OrderDeliveryStatus.choices,
        default=OrderDeliveryStatus.PROCESSING,
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
    # Выбранный тариф и режим доставки
    tariff_code = models.IntegerField(blank=True, null=True)  # Код тарифа, используемого для доставки
    delivery_mode = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="Код режима доставки CDEK",
    )

    delivery_mode_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Режим доставки CDEK",
    )

    # Пункты отправления / получения
    # Пункт, куда клиент/продавец самостоятельно привозит отправление.
    shipment_point = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="ПВЗ отправления CDEK",
    )

    # Соответствует delivery_point API CDEK.
    # Пункт, в который CDEK доставляет отправление.
    delivery_point = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="ПВЗ получения CDEK",
    )

    # Локация отправления, заполняется при delivery_mod "От двери"
    location_from = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Город отправления магазина", )

    location_from_region = models.CharField(
        max_length=255,
        verbose_name="Область/регион магазина",
    )

    location_from_district = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Район магазина",
    )

    location_from_country = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default="Россия",
        verbose_name="Страна магазина",
    )

    address_from = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Адрес отправления",
    )

    postal_code_from = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Почтовый индекс отправления",
    )

    # Локация получения, заполняется при delivery_mod "До двери"
    location_to = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Город получателя", )

    location_to_region = models.CharField(
        max_length=255,
        verbose_name="Область/регион получателя",
    )

    location_to_district = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Район получателя",
    )

    location_to_country = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default="Россия",
        verbose_name="Страна получателя",
    )

    address_to = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Адрес получателя",
    )

    postal_code_to = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Почтовый индекс получателя",
    )

    # Идентификаторы и стоимость
    # Уникальный идентификатор, присваиваемый до валидации заказа в системе CDEK. Этот идентификатор используется
    # для отслеживания заказа до его окончательного подтверждения.
    cdek_uuid = models.CharField(max_length=36, unique=True, null=True, blank=True)  # Уникальный идентификатор груза

    preliminary_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True,
                                            null=True)  # Предварительная стоимость доставки

    # Информация, присваиваемая после подтверждения заказа в системе CDEK.
    shipment_track_id = models.BigIntegerField(blank=True, null=True) # Идентификационный номер отслеживания посылки
    shipment_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # Стоимость доставки

    order_status = models.CharField(max_length=255, blank=True, null=True) # Статус заказа

    stock_status = models.PositiveSmallIntegerField(
        choices=StockReservationStatus.choices,
        default=StockReservationStatus.RESERVED,
    ) # Статус резервирования товара на складе

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


class CdekDeliveryStatusHistory(models.Model):
    cdek_delivery = models.ForeignKey(
        CdekDelivery,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    status_code = models.CharField(
        max_length=100,
    )

    status_name = models.CharField(
        max_length=255,
        blank=True,
    )

    status_date = models.DateTimeField()

    city = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["status_date"]


class CdekRequestLog(models.Model):
    """
        Техническая информация о клиентском возврате
        в системе CDEK.
    """
    cdek_delivery = models.ForeignKey(
        CdekDelivery,
        on_delete=models.CASCADE,
        related_name="request_logs",
        null=True,
        blank=True,
    )

    cdek_uuid = models.UUIDField(
        null=True,
        blank=True,
    )

    request_type = models.CharField(
        max_length=50,
    )

    state = models.CharField(
        max_length=50,
    )

    date_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    error_message = models.TextField(
        blank=True,
        null=True,
    )

    response_data = models.JSONField(
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

class CdekReturn(models.Model):
    return_request = models.OneToOneField(
        "order.ReturnRequest",
        on_delete=models.PROTECT,
        related_name="cdek_return",
        verbose_name="Заявка на возврат",
    )

    cdek_delivery = models.ForeignKey(
        CdekDelivery,
        on_delete=models.PROTECT,
        related_name="returns",
        verbose_name="Исходная доставка CDEK",
    )

    cdek_uuid = models.UUIDField(
        unique=True,
        verbose_name="UUID возврата CDEK",
    )

    tariff_code = models.PositiveIntegerField(
        verbose_name="Тариф CDEK",
    )

    request_state = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Состояние запроса CDEK",
    )

    cdek_status_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Код статуса CDEK",
    )

    cdek_status_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Статус CDEK",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
