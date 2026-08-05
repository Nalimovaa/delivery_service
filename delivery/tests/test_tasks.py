"""
docker exec -it delivery_service-web-1 python manage.py test delivery.tests.test_tasks

Тест Celery-задачи синхронизации тарифов CDEK.

Проверяются два сценария:

1. Если существует хотя бы один магазин с доставкой CDEK:
   - создается экземпляр CDEKTariffService;
   - вызывается sync_cdek_tariffs();
   - результат возвращается вызывающему коду.

2. Если магазинов с доставкой CDEK нет:
   - синхронизация не запускается;
   - сервис CDEKTariffService не создается;
   - задача возвращает статус skipped.
"""

from unittest.mock import patch

from django.test import TestCase

from delivery.models import DeliveryType
from delivery.tasks.tariffs import sync_cdek_tariffs
from seller.models import Shop
from users.models import User


class TariffTaskTest(TestCase):

    @patch("delivery.tasks.tariffs.CDEKTariffService")
    def test_sync_cdek_tariffs(self, mock_service):
        """
        Проверяет выполнение Celery-задачи при наличии
        хотя бы одного магазина с доставкой CDEK.
        """

        user = User.objects.create(
            email="seller@test.com",
        )

        Shop.objects.create(
            owner=user,
            name="Test shop",
            carrier=DeliveryType.CDEK,
        )

        mock_service.return_value.sync_cdek_tariffs.return_value = {
            "processed": 170,
        }

        result = sync_cdek_tariffs()

        self.assertEqual(
            result["processed"],
            170,
        )

        mock_service.assert_called_once()
        mock_service.return_value.sync_cdek_tariffs.assert_called_once()

    @patch("delivery.tasks.tariffs.CDEKTariffService")
    def test_sync_cdek_tariffs_without_cdek_shops(
        self,
        mock_service,
    ):
        """
        Проверяет, что синхронизация не запускается,
        если магазинов с доставкой CDEK нет.
        """

        result = sync_cdek_tariffs()

        self.assertEqual(
            result,
            {
                "processed": 0,
                "status": "skipped",
            },
        )

        mock_service.assert_not_called()