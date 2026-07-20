"""
Базовый интерфейс адаптера службы доставки.

Каждый адаптер должен преобразовать внутренние
данные маркетплейса в формат конкретного API.
"""


from abc import ABC, abstractmethod


class DeliveryAdapter(ABC):
    """
    Абстрактный адаптер службы доставки.
    """

    @abstractmethod
    def calculate_delivery(self, data):
        """
        Расчет стоимости доставки.
        """
        pass

    @abstractmethod
    def create_delivery(self, data):
        """
        Создание отправления.
        """
        pass

    @abstractmethod
    def get_status(self, delivery_id):
        """
        Получение статуса доставки.
        """
        pass

    @abstractmethod
    def cancel_delivery(self, delivery_id):
        """
        Отмена доставки.
        """
        pass