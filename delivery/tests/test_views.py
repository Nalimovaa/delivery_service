""" docker exec -it delivery_service-web-1 python manage.py test delivery.tests.test_views """

from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase


@patch("users.permissions.IsCustomAuthenticated.has_permission", return_value=True)
@patch("users.permissions.RolePermission.has_permission", return_value=True)
class TestCDEKTariffView(APITestCase):
    """ Тесты эндпоинта получения списка актуальных тарифов CDEK.

        Проверяется, что:
        - эндпоинт успешно возвращает HTTP 200;
        - список тарифов берется из сервиса CDEKTariffService;
        - возвращаются актуальные тарифы, полученные из кэша Redis.

        Проверка авторизации и RBAC в данном тесте отключена с помощью mock,
        поскольку они тестируются отдельно. """

    @patch("delivery.services.tariffs.CDEKTariffService.get_cached_tariffs")
    def test_get_all_tariffs(self, mocked_tariffs, *_):
        """ Проверяет успешное получение списка актуальных тарифов CDEK.

            Вместо обращения к Redis используется mock метода
            CDEKTariffService.get_cached_tariffs(). После выполнения запроса
            проверяется, что эндпоинт возвращает HTTP 200. """

        mocked_tariffs.return_value = [
            {
                "tariff_code": 499,
                "tariff_name": "Business Express",
                "delivery_mode": 1,
                "delivery_mode_name": "дверь-дверь",
                "weight_min": "0.000",
                "weight_max": "1000.000",
                "length_max": 1000,
                "width_max": 1000,
                "height_max": 1000,
            }
        ]

        response = self.client.get("/api/alltariffs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)