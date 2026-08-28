from django.db import transaction



class CDEKOrderService:
    """
    Сервис создает CdekDelivery для регистрации заказа в  системе CDEK.
    """

    def __init__(self, user):
        self.user = user

    def _create_cdek_deliveries(self, order_deliveries: list[dict]):
        """
        Создает CdekDelivery для магазина, у которго указан CDEK.
        """

        pass

    def _prepare_cdek_registration(
            self,
            order,
            order_deliveries,
    ):
        """
        Подготавливает данные созданных отправлений
        для последующей асинхронной регистрации в CDEK.
        """

        pass

    @transaction.atomic
    def create_order(
            self,
            selected_tariffs: dict[int, int],
            **kwargs,
    ):
        pass


