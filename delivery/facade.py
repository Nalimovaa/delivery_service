"""
Фасад модуля доставки.

Предоставляет единый интерфейс для бизнес-логики маркетплейса.
Скрывает детали работы с конкретными службами доставки:
- выбор адаптера;
- форматирование данных;
- работу с внешним API.

Бизнес-логика заказа не зависит от реализации CDEK, Boxberry,
DHL и других служб доставки.
"""


class DeliveryFacade:
    """
    Единая точка входа для операций доставки.

    Отвечает за:
    - расчет стоимости доставки;
    - создание отправления;
    - получение статуса;
    - отмену доставки;
    - обработку возвратов.
    """

    class DeliveryFacade:
        """
        Единая точка входа для операций доставки.

        Отвечает за:
        - расчет стоимости доставки;
        - создание отправления;
        - получение статуса;
        - отмену доставки;
        - обработку возвратов.
        """

        def __init__(self, adapter):
            self.adapter = adapter

        def calculate_delivery(self, data):
            """
            Расчет стоимости доставки.
            """
            return self.adapter.calculate_delivery(data)

        def create_delivery(self, data):
            """
            Регистрация отправления в службе доставки.
            """
            return self.adapter.create_delivery(data)

        def get_status(self, delivery_id):
            """
            Получение текущего статуса доставки.
            """
            return self.adapter.get_status(delivery_id)

        def cancel_delivery(self, delivery_id):
            """
            Отмена отправления.
            """
            return self.adapter.cancel_delivery(delivery_id)
