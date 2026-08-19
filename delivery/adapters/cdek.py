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
from delivery.routes.routes_cdek import CALCULATOR_ALL_TARIFFS, CALCULATOR_TARIFF_LIST, CALCULATOR_TARIFF, \
    CITIES_SUGGEST
from delivery.schemas.tariffs import AvailableTariffsResponseSchema, TariffListResponseSchema, CDEKCitySchema, \
    CDEKCityErrorResponseSchema, TariffCalculationResponseSchema


class CDEKAdapter(DeliveryAdapter):

    def __init__(self):
        self.client = CDEKClient()

    def get_all_tariffs(self) -> AvailableTariffsResponseSchema:
        """
        Получение всех доступных тарифов
        по договору продавца.
        """

        response = self.client.get(CALCULATOR_ALL_TARIFFS)

        schema = AvailableTariffsResponseSchema.model_validate(
            response
        )

        if schema.errors:
            messages = [
                error.get("message", "Неизвестная ошибка")
                for error in schema.errors
            ]

            raise CDEKBusinessError(
                operation="get_all_tariffs",
                code=schema.errors[0].get("code"),
                message="; ".join(messages),
                response_data=response,
            )

        return schema # возвращает Pydantic-модель

    def suggest_cities(
            self,
            name: str,
            country_code: str = "RU",
    ) -> list[CDEKCitySchema]:
        """Метод СДЭКа 'Подбор локации по названию города'."""

        params = {
            "name": name,
            "country_code": country_code,
        }

        response = self.client.get(
            CITIES_SUGGEST,
            params=params,
        )

        # Ответ с ошибкой от CDEK
        if isinstance(response, dict) and response.get("errors"):
            error_schema = CDEKCityErrorResponseSchema.model_validate(
                response
            )

            messages = [
                error.message
                for error in error_schema.errors
            ]

            raise CDEKBusinessError(
                operation="suggest_cities",
                code=error_schema.errors[0].code,
                message="; ".join(messages),
                response_data=response,
            )

        # Успешный ответ — список городов
        schema = [
            CDEKCitySchema.model_validate(city)
            for city in response
        ]

        return schema

    def generate_data_tariff_and_services(
            self,
            *,
            from_location_code: int,
            to_location_code: int,
            items,
            services=None,
            additional_order_types=None,
            shipment_point=None,
            delivery_point=None,
            currency=None,
            date=None,
    ):
        """Формирование данных для def pre_calculate_delivery()
        Отвечает за:
        - сформировать packages из переданных CartItem;
        - вызвать API CDEK;
        - преобразовать ответ в TariffListResponseSchema."""

        packages = []

        for item in items:
            product = item.unique_product

            package = {
                "weight": product.weight * item.amount,
            }

            # if product.length:
            #     package["length"] = product.length
            #
            # if product.width:
            #     package["width"] = product.width
            #
            # if product.height:
            #     package["height"] = product.height

            packages.append(package)

        data = {
            "type": 1,
            "lang": "rus",
            "from_location": {
                # "code": from_location_code,
                "postal_code": 443114,
            },
            "to_location": {
                # "code": to_location_code,
                "postal_code": 443115,
            },
            "packages": packages,
            "services": services or [],
        }

        if additional_order_types:
            data["additional_order_types"] = additional_order_types

        if shipment_point:
            data["shipment_point"] = shipment_point

        if delivery_point:
            data["delivery_point"] = delivery_point

        if currency:
            data["currency"] = currency

        if date:
            data["date"] = date

        return data

    def pre_calculate_delivery(
            self,
            *,
            from_location_code: int,
            to_location_code: int,
            items,
            services=None,
            additional_order_types=None,
            shipment_point=None,
            delivery_point=None,
            currency=None,
            date=None,
    ) -> TariffListResponseSchema:
        """ Предварительный расчет доставки.
        До оформления Order расчет доступных вариантов доставки (список тарифов для товаров в корзине).
        """

        data = self.generate_data_tariff_and_services(
            from_location_code=from_location_code,
            to_location_code=to_location_code,
            items=items,
            services=services,
            additional_order_types=additional_order_types,
            shipment_point=shipment_point,
            delivery_point=delivery_point,
            currency=currency,
            date=date,
        )

        response = self.client.post(
            CALCULATOR_TARIFF_LIST,
            json=data,
        )

        schema = TariffListResponseSchema.model_validate(response)

        if schema.errors:
            messages = [
                error.get("message", "Неизвестная ошибка")
                for error in schema.errors
            ]

            raise CDEKBusinessError(
                operation="pre_calculate_delivery",
                code=schema.errors[0].get("code"),
                message="; ".join(messages),
                response_data=response,
            )

        return schema # возвращает Pydantic-модель

    def generate_data_calculate_by_tariff_code(
            self,
            *,
            tariff_code: int,
            from_location_code: int,
            to_location_code: int,
            items,
            services=None,
            additional_order_types=None,
            shipment_point=None,
            delivery_point=None,
            currency=None,
            date=None,
    ):
        """Формирование данных для def calculate_delivery()
        Отвечает за:
        - сформировать packages из переданных CartItem;
        - вызвать API CDEK;
        - преобразовать ответ в TariffCalculationResponseSchema."""

        packages = []

        for item in items:
            product = item.unique_product

            package = {
                "weight": product.weight * item.amount,
            }

            # if product.length:
            #     package["length"] = product.length
            #
            # if product.width:
            #     package["width"] = product.width
            #
            # if product.height:
            #     package["height"] = product.height

            packages.append(package)

        data = {
            "type": 1,
            "lang": "rus",
            "tariff_code": tariff_code,
            "from_location": {
                # "code": from_location_code,
                "postal_code": 443114,
            },
            "to_location": {
                # "code": to_location_code,
                "postal_code": 443115,
            },
            "packages": packages,
            "services": services or [],
        }

        if additional_order_types:
            data["additional_order_types"] = additional_order_types

        if shipment_point:
            data["shipment_point"] = shipment_point

        if delivery_point:
            data["delivery_point"] = delivery_point

        if currency:
            data["currency"] = currency

        if date:
            data["date"] = date

        return data

    def calculate_delivery(
            self,
            *,
            tariff_code: int,
            from_location_code: int,
            to_location_code: int,
            items,
            services=None,
            additional_order_types=None,
            shipment_point=None,
            delivery_point=None,
            currency=None,
            date=None,
    ) -> TariffCalculationResponseSchema:
        """
        Финальный расчет стоимости выбранного тарифа.
        Расчёт стоимости доставки по конкретному коду тарифа.

        :param tariff_code: Код тарифа СДЭК
        :param from_location_code: Код города отправления
        :param to_location_code: Код города получения
        :param items: Список CartItem
        :param services: Список дополнительных услуг
        :param additional_order_types: Дополнительные типы заказа
        :param shipment_point: Код ПВЗ для привоза
        :param delivery_point: Код ПВЗ для доставки
        :param currency: Валюта расчёта
        :param date: Дата планируемой передачи заказа
        :return: Валидированная Pydantic-схема ответа
        """
        data = self.generate_data_calculate_by_tariff_code(
            from_location_code=from_location_code,
            to_location_code=to_location_code,
            tariff_code=tariff_code,
            items=items,
            services=services,
            additional_order_types=additional_order_types,
            shipment_point=shipment_point,
            delivery_point=delivery_point,
            currency=currency,
            date=date,
        )

        # 4. Выполняем POST-запрос к API СДЭК
        response = self.client.post(CALCULATOR_TARIFF, json=data)

        schema = TariffCalculationResponseSchema.model_validate(response)

        if schema.errors:
            messages = [
                error.get("message", "Неизвестная ошибка")
                for error in schema.errors
            ]

            raise CDEKBusinessError(
                operation="calculate_by_tariff_code",
                code=schema.errors[0].get("code"),
                message="; ".join(messages),
                response_data=response,
            )

        return schema  # возвращает Pydantic-модель

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

