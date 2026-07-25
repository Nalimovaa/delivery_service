"""
python manage.py test delivery.tests.test_tariffs

Тесты бизнес-логики синхронизации тарифов CDEK.

Проверяется работа сервиса CDEKTariffService:
- подготовка данных из ответа API СДЭК;
- преобразование Pydantic-схем в структуру для сохранения;
- сохранение тарифов в PostgreSQL;
- возврат количества обработанных тарифов.

В тестах не используется реальный API СДЭК.
Ответ API заменяется тестовой Pydantic-моделью AvailableTariffsResponseSchema.
Это позволяет проверить только бизнес-логику сервиса без зависимости от внешнего сервиса.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from delivery.schemas.tariffs import (
    AvailableTariffsResponseSchema,
    AvailableTariffSchema,
    TariffDeliveryModeSchema,
)

from delivery.services.tariffs import CDEKTariffService
from delivery.models import CDEKTariff


class CDEKTariffServiceTest(TestCase):

    def setUp(self):
        """ Подготовка экземпляра сервиса перед каждым тестом. """
        self.service = CDEKTariffService()

    def get_mock_response(self):
        """ Формирование тестового ответа API СДЭК.

            Имитирует ответ метода получения доступных тарифов:
                - один тариф;
                - два режима доставки;
                - два тарифных кода.

            Используется вместо реального HTTP-запроса к CDEK API. """

        return AvailableTariffsResponseSchema(
            tariff_codes=[
                AvailableTariffSchema(
                    tariff_name="Экономичная посылка",
                    weight_min=Decimal("0"),
                    weight_max=Decimal("50"),
                    weight_calc_max=Decimal("50"),

                    length_min=0,
                    length_max=150,

                    width_min=0,
                    width_max=150,

                    height_min=0,
                    height_max=150,

                    delivery_modes=[
                        TariffDeliveryModeSchema(
                            delivery_mode=1,
                            delivery_mode_name="дверь-дверь",
                            tariff_code=231,
                        ),
                        TariffDeliveryModeSchema(
                            delivery_mode=2,
                            delivery_mode_name="дверь-склад",
                            tariff_code=232,
                        ),
                    ],
                )
            ]
        )


    def test_prepare_tariffs(self):
        """
            Проверка подготовки тарифов перед сохранением.

            Метод prepare_tariffs():
                - принимает объект AvailableTariffsResponseSchema;
                - разворачивает режимы доставки;
                - формирует список словарей для записи в БД.

            Проверяется:
                - количество подготовленных тарифов;
                - корректность кода тарифа;
                - корректность названия тарифа.
        """
        response = self.get_mock_response()

        tariffs = list(
            self.service.prepare_tariffs(response)
        )

        self.assertEqual(len(tariffs), 2)

        self.assertEqual(
            tariffs[0]["tariff_code"],
            231
        )

        self.assertEqual(
            tariffs[0]["tariff_name"],
            "Экономичная посылка"
        )


    @patch(
        "delivery.services.tariffs.CDEKTariffService.fetch_tariffs"
    )
    def test_sync_cdek_tariffs(self, mock_fetch):
        """
            Проверка полной синхронизации тарифов.

            Реальный запрос к CDEK API заменяется mock-ответом.

            Проверяется полный сценарий:
                1. получение тарифов;
                2. подготовка данных;
                3. сохранение в PostgreSQL;
                4. возврат количества обработанных тарифов.

            Ожидаемый результат:
                - создано 2 записи CDEKTariff;
                - возвращено количество обработанных тарифов = 2;
                - тариф активен.
        """

        mock_fetch.return_value = self.get_mock_response()


        result = self.service.sync_cdek_tariffs()


        self.assertEqual(
            result["processed"],
            2
        )


        self.assertEqual(
            CDEKTariff.objects.count(),
            2
        )


        tariff = CDEKTariff.objects.first()

        self.assertEqual(
            tariff.tariff_code,
            231
        )

        self.assertTrue(
            tariff.is_active
        )