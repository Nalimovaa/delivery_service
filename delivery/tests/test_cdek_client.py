"""
python manage.py test delivery.tests.test_cdek_client
"""

import unittest

from delivery.adapters.cdek import CDEKAdapter


class CDEKAdapterTestCase(unittest.TestCase):
    """
    Интеграционные тесты подключения к API СДЭК.
    Требуют наличия корректных CDEK_* переменных окружения
    и доступа к тестовому API СДЭК.
    """

    def setUp(self):
        self.adapter = CDEKAdapter()

    def test_singleton_client(self):
        """
        Все адаптеры должны использовать один экземпляр CDEKClient.
        """
        adapter2 = CDEKAdapter()

        self.assertIs(
            self.adapter.client,
            adapter2.client,
        )

    def test_authentication(self):
        """
        Клиент должен успешно получать OAuth-токен.
        """
        self.assertIsNone(
            self.adapter.client._access_token
        )

        self.adapter.client._ensure_authenticated()

        self.assertIsNotNone(
            self.adapter.client._access_token
        )

        self.assertIsNotNone(
            self.adapter.client._expires_at
        )

    def test_get_all_tariffs(self):
        """
        Получение списка тарифов должно завершаться успешно.
        """
        result = self.adapter.get_all_tariffs()

        self.assertIsInstance(result, dict)
        self.assertIn("tariff_codes", result)
        self.assertGreater(len(result["tariff_codes"]), 0)