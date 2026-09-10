"""
Адаптер API службы доставки CDEK.

Отвечает за:
- преобразование внутренних данных заказа в формат CDEK API;
- вызов методов CDEKClient;
- обработку бизнес-ответов;
- преобразование ответа CDEK во внутреннюю модель доставки.
"""

from decimal import Decimal
from delivery.adapters.base import DeliveryAdapter
from delivery.client import CDEKClient
from delivery.enums import CDEKDeliveryMode
from delivery.exceptions import CDEKBusinessError
from delivery.routes.routes_cdek import CALCULATOR_ALL_TARIFFS, CALCULATOR_TARIFF_LIST, CALCULATOR_TARIFF, \
    CITIES_SUGGEST, CDEK_CITIES, DELIVERY_POINTS, CDEK_POSTALCODES, CDEK_ORDER_UUID, CDEK_ORDERS, CDEK_WEBHOOKS, \
    CDEK_WEBHOOK_UUID
from delivery.schemas.locations import CDEKCitiesSchema, CDEKCitiesErrorResponseSchema, \
    CDEKDeliveryPointsErrorResponseSchema, CDEKDeliveryPointSchema, CDEKPostalCodesResponseSchema, \
    CDEKPostalCodesErrorResponseSchema
from delivery.schemas.order import CDEKOrderResponseSchema, CDEKOrderCreateResponseSchema
from delivery.schemas.tariffs import AvailableTariffsResponseSchema, TariffListResponseSchema, CDEKCitySchema, \
    CDEKCityErrorResponseSchema, TariffCalculationResponseSchema
from delivery.schemas.weebhooks import WebhookSchema, WebhookDeleteResponseSchema, WebhookSubscriptionResponseSchema, \
    WebhookSubscriptionRequestSchema
from uuid import UUID
from pydantic import TypeAdapter


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
                "code": from_location_code,
                # "postal_code": 443114,
            },
            "to_location": {
                "code": to_location_code,
                # "postal_code": 443115,
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
                "code": from_location_code,
                # "postal_code": 443114,
            },
            "to_location": {
                "code": to_location_code,
                # "postal_code": 443115,
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

    def get_cities(
            self,
            *,
            country_codes: str = "RU",
            size: int = 1000,
            page: int = 0,
            region_code: int | None = None,
            kladr_region_code: str | None = None,
            fias_region_guid: str | None = None,
            kladr_code: str | None = None,
            fias_guid: str | None = None,
            postal_code: str | None = None,
            code: int | None = None,
            city: str | None = None,
            payment_limit: float | None = None,
            lang: str = "RU",
    ) -> list[CDEKCitiesSchema]:
        """
        Получение списка населенных пунктов СДЭК.

        Можно ограничить выборку по стране, региону,
        коду населенного пункта, названию города и другим параметрам.
        """

        params = {
            "country_codes": country_codes,
            "size": size,
            "page": page,
            "region_code": region_code,
            "kladr_region_code": kladr_region_code,
            "fias_region_guid": fias_region_guid,
            "kladr_code": kladr_code,
            "fias_guid": fias_guid,
            "postal_code": postal_code,
            "code": code,
            "city": city,
            "payment_limit": payment_limit,
            "lang": lang,
        }

        params = {
            key: value
            for key, value in params.items()
            if value is not None
        }

        response = self.client.get(
            CDEK_CITIES,
            params=params,
        )

        if isinstance(response, list):
            return [
                CDEKCitiesSchema.model_validate(city_data)
                for city_data in response
            ]

        error_schema = CDEKCitiesErrorResponseSchema.model_validate(
            response
        )

        messages = [
            error.message
            for error in error_schema.errors
        ]

        raise CDEKBusinessError(
            operation="get_cities",
            code=(
                error_schema.errors[0].code
                if error_schema.errors
                else None
            ),
            message="; ".join(messages),
            response_data=response,
        )

    def get_postalcodes(
            self,
            *,
            code: int,
    ) -> CDEKPostalCodesResponseSchema:
        """
        Получение списка почтовых индексов
        для населенного пункта CDEK.

        :param code: Код населенного пункта CDEK.
        :return: Валидированная Pydantic-модель
            с кодом города и списком почтовых индексов.
        """

        params = {
            "code": code,
        }

        response = self.client.get(
            CDEK_POSTALCODES,
            params=params,
        )

        if isinstance(response, dict) and "postal_codes" in response:
            return CDEKPostalCodesResponseSchema.model_validate(
                response
            )

        error_schema = (
            CDEKPostalCodesErrorResponseSchema.model_validate(
                response
            )
        )

        messages = [
            error.message
            for error in error_schema.errors
        ]

        raise CDEKBusinessError(
            operation="get_postalcodes",
            code=(
                error_schema.errors[0].code
                if error_schema.errors
                else None
            ),
            message="; ".join(messages),
            response_data=response,
        )

    def get_delivery_points(
            self,
            *,
            country_code: str = "RU",
    ) -> list[CDEKDeliveryPointSchema]:
        """
        Получение списка пунктов выдачи и приема CDEK.

        По умолчанию возвращаются только пункты,
        расположенные на территории России.
        """

        params = {
            "country_code": country_code,
        }

        response = self.client.get(
            DELIVERY_POINTS,
            params=params,
        )

        if isinstance(response, list):
            return [
                CDEKDeliveryPointSchema.model_validate(
                    delivery_point
                )
                for delivery_point in response
            ]

        error_schema = (
            CDEKDeliveryPointsErrorResponseSchema.model_validate(
                response
            )
        )

        messages = [
            error.message
            for error in error_schema.errors
        ]

        raise CDEKBusinessError(
            operation="get_delivery_points",
            code=(
                error_schema.errors[0].code
                if error_schema.errors
                else None
            ),
            message="; ".join(messages),
            response_data=response,
        )

    def generate_order_item(
            self,
            *,
            ware_key: str,
            name: str,
            cost: Decimal,
            amount: int,
            weight: int,
            payment: Decimal = Decimal("0"),
    ) -> dict:
        """
        Формирование товарной позиции для регистрации заказа CDEK (для def generate_data_order()).

        :param ware_key: Артикул товара.
        :param name: Название товара на момент оформления заказа.
        :param cost: Цена одной единицы товара.
        :param amount: Количество единиц товара.
        :param weight: Вес одной единицы товара в граммах.
        :param payment: Сумма наложенного платежа.
        """

        return {
            "ware_key": ware_key,
            "payment": {
                "value": float(payment),
            },
            "name": name,
            "cost": float(cost),
            "amount": amount,
            "weight": weight,
        }

    def generate_order_service(
            self,
            *,
            code: str,
            parameter=None,
    ) -> dict:
        """
        Формирование дополнительной услуги заказа CDEK (для def generate_data_order()).

        :param code: Код дополнительной услуги.
        :param parameter: Параметр дополнительной услуги.
        """

        service = {
            "code": code,
        }

        if parameter is not None:
            service["parameter"] = parameter

        return service

    def generate_from_location(
            self,
            *,
            code: int | None = None,
            country_code: str = "RU",
            region_code: int | None = None,
            address: str,
            postal_code: str | None = None,
    ) -> dict:
        """
        Формирование адреса отправления для заказа CDEK (для def generate_data_order()).
        Используется для тарифов, начинающихся от двери.
        """

        data = {
            "country_code": country_code,
            "address": address,
        }

        if code is not None:
            data["code"] = code

        if region_code is not None:
            data["region_code"] = region_code

        if postal_code:
            data["postal_code"] = postal_code

        return data

    def generate_to_location(
            self,
            *,
            code: int | None = None,
            country_code: str = "RU",
            region_code: int | None = None,
            address: str,
            postal_code: str | None = None,
    ) -> dict:
        """
        Формирование адреса получения для заказа CDEK (для def generate_data_order()).
        Используется для тарифов, заканчивающихся у двери.
        """

        data = {
            "country_code": country_code,
            "address": address,
        }

        if code is not None:
            data["code"] = code

        if region_code is not None:
            data["region_code"] = region_code

        if postal_code:
            data["postal_code"] = postal_code

        return data

    def generate_order_package(
            self,
            *,
            number: str,
            weight: int,
            items: list[dict],
            comment: str | None = None,
            height: int | None = None,
            length: int | None = None,
            width: int | None = None,
    ) -> dict:
        """
        Формирование упаковки заказа CDEK (для def generate_data_order()).

        :param number: Номер упаковки.
        :param weight: Общий вес упаковки в граммах.
        :param items: Товарные позиции внутри упаковки.
        """

        package = {
            "number": number,
            "weight": weight,
            "items": items,
        }

        if comment:
            package["comment"] = comment

        if height is not None:
            package["height"] = height

        if length is not None:
            package["length"] = length

        if width is not None:
            package["width"] = width

        return package

    def generate_order_sender(
            self,
            *,
            company: str,
            name: str,
            contragent_type: str,
            phone: str,
            passport_requirements_satisfied: bool = False,
    ) -> dict:
        """
        Формирование данных отправителя для регистрации заказа CDEK
        (для def generate_data_order()).

        :param company:
            Название компании отправителя.
        :param name:
            Наименование/ФИО отправителя.
        :param contragent_type:
            Тип контрагента CDEK, например LEGAL_ENTITY.
        :param phone:
            Номер телефона отправителя.
        :param passport_requirements_satisfied:
            Признак выполнения требований по паспорту.
        """

        return {
            "company": company,
            "name": name,
            "contragent_type": contragent_type,
            "phones": [
                {
                    "number": phone,
                }
            ],
            "passport_requirements_satisfied": (
                passport_requirements_satisfied
            ),
        }

    def generate_order_recipient(
            self,
            *,
            name: str,
            phone: str,
    ) -> dict:
        """
        Формирование данных получателя для регистрации заказа CDEK
        (для def generate_data_order()).

        :param name:
            ФИО получателя.
        :param phone:
            Номер телефона получателя.
        """

        return {
            "name": name,
            "phones": [
                {
                    "number": phone,
                }
            ],
        }

    def generate_data_order(
            self,
            *,
            number: str,
            comment: str,
            tariff_code: int,
            delivery_mode: CDEKDeliveryMode,
            sender: dict,
            recipient: dict,
            packages: list[dict],
            services: list[dict] | None = None,
            shipment_point: str | None = None,
            delivery_point: str | None = None,
            from_location: dict | None = None,
            to_location: dict | None = None,
            is_client_return: bool = False,
            additional_order_types: list[int] | None = None,
    ) -> dict:
        """
        Формирование данных для регистрации заказа
        в системе CDEK (для def post_order()).

        Формирует payload для POST /v2/orders.

        В зависимости от режима доставки определяет,
        какие данные необходимо передать:
        - from_location / shipment_point;
        - to_location / delivery_point.

        :param number:
            Номер заказа в ИС клиента.
        :param comment:
            Комментарий к заказу.
        :param tariff_code:
            Код тарифа CDEK.
        :param delivery_mode:
            Режим доставки CDEK.
        :param sender:
            Данные отправителя.
        :param recipient:
            Данные получателя.
        :param packages:
            Список упаковок.
        :param services:
            Дополнительные услуги CDEK.
        :param shipment_point:
            Код ПВЗ/склада отправления CDEK.
        :param delivery_point:
            Код ПВЗ/склада получения CDEK.
        :param from_location:
            Адрес отправления.
        :param to_location:
            Адрес получения.
        :param is_client_return:
            Признак клиентского возврата.
        :param additional_order_types:
            Дополнительные типы заказа.

        :return:
            Словарь с данными для регистрации заказа.
        """

        data = {
            "type": 1,
            "number": number,
            "comment": comment,
            "is_client_return": is_client_return,
            "tariff_code": tariff_code,
            "sender": sender,
            "recipient": recipient,
            "packages": packages,
            "services": services or [],
        }

        # Откуда
        #
        # Режимы, начинающиеся с двери:
        # 1 — дверь-дверь
        # 2 — дверь-склад
        # 6 — дверь-постамат
        if delivery_mode in {
            CDEKDeliveryMode.DOOR_TO_DOOR,
            CDEKDeliveryMode.DOOR_TO_WAREHOUSE,
            CDEKDeliveryMode.DOOR_TO_POSTAMAT,
        }:
            if from_location is None:
                raise ValueError(
                    "Для режима доставки от двери "
                    "необходимо передать from_location."
                )

            data["from_location"] = from_location

        # Режимы, начинающиеся со склада / ПВЗ / постамата /
        # терминала.
        else:
            if shipment_point is None:
                raise ValueError(
                    "Для режима доставки от склада "
                    "необходимо передать shipment_point."
                )

            data["shipment_point"] = shipment_point

        # Куда
        #
        # Режимы, заканчивающиеся у двери:
        # 1 — дверь-дверь
        # 3 — склад-дверь
        # 8 — постамат-дверь
        if delivery_mode in {
            CDEKDeliveryMode.DOOR_TO_DOOR,
            CDEKDeliveryMode.WAREHOUSE_TO_DOOR,
            CDEKDeliveryMode.POSTAMAT_TO_DOOR,
        }:
            if to_location is None:
                raise ValueError(
                    "Для режима доставки до двери "
                    "необходимо передать to_location."
                )

            data["to_location"] = to_location

        # Режимы, заканчивающиеся на склад / ПВЗ /
        # постамат / терминал.
        else:
            if delivery_point is None:
                raise ValueError(
                    "Для режима доставки до склада "
                    "необходимо передать delivery_point."
                )

            data["delivery_point"] = delivery_point

        if additional_order_types:
            data["additional_order_types"] = additional_order_types

        return data

    def create_delivery(
            self,
            *,
            data: dict,
    ) -> CDEKOrderCreateResponseSchema:
        """
        Регистрация заказа в системе CDEK.

        Важно:
        CDEK работает асинхронно. Ответ со state=ACCEPTED
        означает только то, что запрос принят системой CDEK.
        Для подтверждения фактического создания заказа
        необходимо дополнительно получить заказ по UUID.

        :param data: Данные заказа для регистрации в CDEK.
        :return: Валидированный ответ CDEK с UUID заказа
            и состоянием запроса.
        """

        response = self.client.post(
            CDEK_ORDERS,
            json=data,
        )

        invalid_requests = [
            request
            for request in response.get("requests", [])
            if request.get("state") == "INVALID"
        ]

        if invalid_requests:
            request = invalid_requests[0]

            errors = request.get("errors", [])

            messages = [
                error.get("message")
                for error in errors
                if error.get("message")
            ]

            raise CDEKBusinessError(
                operation="post_order",
                code=(
                    errors[0].get("code")
                    if errors
                    else None
                ),
                message="; ".join(messages),
                response_data=response,
            )

        return CDEKOrderCreateResponseSchema.model_validate(
            response,
        )

    def get_order_uuid(
            self,
            *,
            uuid: str,
    ) -> CDEKOrderResponseSchema:
        """
        Получение информации о заказе CDEK по UUID.

        :param uuid: UUID заказа в системе CDEK.
        :return: Валидированная Pydantic-модель
            с информацией о заказе.
        """

        endpoint = CDEK_ORDER_UUID.format(
            uuid=uuid,
        )

        response = self.client.get(
            endpoint,
        )

        invalid_requests = [
            request
            for request in response.get("requests", [])
            if request.get("state") == "INVALID"
        ]

        if invalid_requests:
            request = invalid_requests[0]
            errors = request.get("errors", [])

            messages = [
                error.get("message")
                for error in errors
                if error.get("message")
            ]

            raise CDEKBusinessError(
                operation="get_order_uuid",
                code=(
                    errors[0].get("code")
                    if errors
                    else None
                ),
                message="; ".join(messages),
                response_data=response,
            )

        return CDEKOrderResponseSchema.model_validate(
            response,
        )

    def get_status(
            self,
            *,
            cdek_number: str,
    ) -> CDEKOrderResponseSchema:
        """
        Проверка статуса заказа по номеру СДЭК (cdek_number)

        :param cdek_number: Номер заказа в системе CDEK.
        :return: Валидированная Pydantic-модель
            с информацией о заказе.
        """

        params = {
            "cdek_number": cdek_number,
        }

        response = self.client.get(
            CDEK_ORDERS,
            params=params,
        )

        invalid_requests = [
            request
            for request in response.get("requests", [])
            if request.get("state") == "INVALID"
        ]

        if invalid_requests:
            request = invalid_requests[0]
            errors = request.get("errors", [])

            messages = [
                error.get("message")
                for error in errors
                if error.get("message")
            ]

            raise CDEKBusinessError(
                operation="get_order_cdek_number",
                code=(
                    errors[0].get("code")
                    if errors
                    else None
                ),
                message="; ".join(messages),
                response_data=response,
            )

        return CDEKOrderResponseSchema.model_validate(
            response,
        )

    def subscribe_to_order_status_webhook(
            self,
            url: str,
    ) -> WebhookSubscriptionResponseSchema:
        data = WebhookSubscriptionRequestSchema(
            type="ORDER_STATUS",
            url=url,
        ).model_dump()

        response = self.client.post(
            CDEK_WEBHOOKS,
            json=data,
        )

        schema = WebhookSubscriptionResponseSchema.model_validate(
            response
        )

        return schema

    def get_all_webhooks(
            self,
    ) -> list[WebhookSchema]:
        response = self.client.get(
            CDEK_WEBHOOKS,
        )

        return TypeAdapter(
            list[WebhookSchema]
        ).validate_python(response)

    def get_webhook(
            self,
            uuid: str | UUID,
    ) -> WebhookSubscriptionResponseSchema:
        response = self.client.get(
            CDEK_WEBHOOK_UUID.format(uuid=uuid),
        )

        return WebhookSubscriptionResponseSchema.model_validate(
            response
        )

    def delete_webhook(
            self,
            uuid: str | UUID,
    ) -> WebhookDeleteResponseSchema:
        response = self.client.delete(
            CDEK_WEBHOOK_UUID.format(uuid=uuid),
        )

        return WebhookDeleteResponseSchema.model_validate(
            response
        )

    def cancel_delivery(self, delivery_id):
        raise NotImplementedError

