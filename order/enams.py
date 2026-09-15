from django.db import models


class OrderStatus(models.IntegerChoices):
    """
    Enum for order statuses.
    """
    PROCESSING = 1, "В обработке"
    CONFIRMED = 2, "Подтверждён"
    PARTIALLY_FAILED = 3, "Частично с ошибкой"
    PARTIALLY_DELIVERED = 4, "Частично доставлен"
    COMPLETED = 5, "Завершён"
    FAILED = 6, "Ошибка"
    CANCELLED = 7, "Отменён"


class OrderDeliveryStatus(models.IntegerChoices):
    """
    Унифицированные статусы отправления.
    Не зависят от конкретной транспортной компании.
    """

    PROCESSING = 1, "В обработке"
    CONFIRMED = 2, "Подтверждена"
    IN_TRANSIT = 3, "В пути"
    DELIVERED = 4, "Доставлена"
    FAILED = 5, "Ошибка"
    CANCELLED = 6, "Отменена"


class ReturnRequestStatus(models.IntegerChoices):
    """Для статусов запроса покупателя на возврат товара"""
    REQUESTED = 1, "На рассмотрении"
    APPROVED = 2, "Одобрена"
    REJECTED = 3, "Отклонена"