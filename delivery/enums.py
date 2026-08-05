from django.db import models

class DeliveryType(models.IntegerChoices):
    CDEK = 1, "СДЭК"
    # Добавьте другие типы доставки по мере необходимости:
    BOXBERRY = 2, "Boxberry"
    # POST = 3, "Почта России"