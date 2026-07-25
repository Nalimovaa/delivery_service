"""
Адаптер API службы доставки CDEK.

Отвечает за:
- преобразование внутренних данных заказа в формат CDEK API;
- вызов методов CDEKClient;
- обработку бизнес-ответов;
- преобразование ответа CDEK во внутреннюю модель доставки.
"""


from delivery.adapters.base import DeliveryAdapter
from delivery.client import CDEKClient
from delivery.exceptions import CDEKBusinessError
from delivery.routes.routes_cdek import CALCULATOR_ALL_TARIFFS, CALCULATOR_TARIFF_LIST, CALCULATOR_TARIFF
from delivery.schemas.tariffs import AvailableTariffsResponseSchema


class CDEKAdapter(DeliveryAdapter):

    def __init__(self):
        self.client = CDEKClient()

    def get_all_tariffs(self) -> AvailableTariffsResponseSchema:
        """
        Получение всех доступных тарифов
        по договору продавца.
        """

        response = self.client.get(CALCULATOR_ALL_TARIFFS)

        return AvailableTariffsResponseSchema.model_validate(response) # возвращает Pydantic-модель

    def get_available_tariffs(self, data):
        """
        Расчет доступных вариантов доставки.
        """

        return self.client.post(
            CALCULATOR_TARIFF_LIST,
            json=data
        )

    def calculate_by_tariff_code(
            self,
            data
    ):
        """
        Финальный расчет стоимости
        выбранного тарифа.
        """

        return self.client.post(
            CALCULATOR_TARIFF,
            json=data
        )

    def calculate_delivery(self, data):
        raise NotImplementedError

    def create_delivery(self, data):
        """Успешное создание заказа в системе СДЭК"""
        result = self.post_order(data)

        uuid = (
            result
            .get("entity", {})
            .get("uuid")
        )

        if not uuid:
            raise CDEKBusinessError(
                operation="CREATE",
                message="CDEK uuid отсутствует"
            )

        status = self.get_order_uuid(uuid)

        return status

    def post_order(self, data):
        """Регистрация заказа в системе СДЭК"""
        return self.client.post(
            "/orders",
            json=data
        )

    def get_order_uuid(
            self,
            uuid: str
    ):
        """Проверка создания заказа в ситеме СДЭК"""

        result = self.client.get(
            f"/orders/{uuid}"
        )

        request = (
            result
            .get("requests", [{}])[0]
        )

        if request.get("state") == "INVALID":
            error = request["errors"][0]

            raise CDEKBusinessError(
                operation=request["type"],
                code=error["code"],
                message=error["message"],
                response_data=result
            )

        return result

    def get_status(
            self,
            cdek_number: str
    ):
        """ Проверка статуса заказа по номеру СДЭК (cdek_number) """

        return self.client.get(
            f"/orders?cdek_number={cdek_number}"
        )

    def cancel_delivery(self, delivery_id):
        raise NotImplementedError
