from django.db import models

class DeliveryType(models.IntegerChoices):
    """Типы доставки"""
    CDEK = 1, "СДЭК"
    # Добавьте другие типы доставки по мере необходимости:
    BOXBERRY = 2, "Boxberry"
    # POST = 3, "Почта России"


class CDEKDeliveryMode(models.IntegerChoices):
    """Режимы доставки СДЭК."""

    DOOR_TO_DOOR = 1, "Дверь-дверь"
    DOOR_TO_WAREHOUSE = 2, "Дверь-склад"
    WAREHOUSE_TO_DOOR = 3, "Склад-дверь"
    WAREHOUSE_TO_WAREHOUSE = 4, "Склад-склад"
    TERMINAL_TO_TERMINAL = 5, "Терминал-терминал"
    DOOR_TO_POSTAMAT = 6, "Дверь-постамат"
    WAREHOUSE_TO_POSTAMAT = 7, "Склад-постамат"
    POSTAMAT_TO_DOOR = 8, "Постамат-дверь"
    POSTAMAT_TO_WAREHOUSE = 9, "Постамат-склад"
    POSTAMAT_TO_POSTAMAT = 10, "Постамат-постамат"