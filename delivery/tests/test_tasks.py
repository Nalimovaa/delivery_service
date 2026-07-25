"""
python manage.py test delivery.tests.test_tasks

Тест Celery-задачи синхронизации тарифов CDEK.

Проверяется корректная связь между:
Celery Task -> CDEKTariffService -> sync_cdek_tariffs()

Реальный сервис заменяется mock-объектом,
чтобы тестировать только поведение Celery-задачи
без обращения к базе данных и внешнему API СДЭК.

Проверяется:
- создание экземпляра CDEKTariffService;
- вызов метода синхронизации;
- возврат результата выполнения задачи.
"""

from unittest.mock import patch

from django.test import TestCase

from delivery.tasks.tariffs import sync_cdek_tariffs


class TariffTaskTest(TestCase):

    @patch(
        "delivery.tasks.tariffs.CDEKTariffService"
    )
    def test_sync_cdek_tariffs(self, mock_service):
        """
            Проверка выполнения Celery-задачи.

            Celery-задача вызывает сервис синхронизации тарифов
            и возвращает результат обработки.

            Проверяется:
                - сервис создается;
                - метод sync_cdek_tariffs вызывается один раз;
                - количество обработанных тарифов передается обратно.
        """

        mock_service.return_value.sync_cdek_tariffs.return_value = {
            "processed": 170
        }

        result = sync_cdek_tariffs()

        self.assertEqual(result["processed"], 170)

        mock_service.assert_called_once()
        mock_service.return_value.sync_cdek_tariffs.assert_called_once()