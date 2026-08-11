# docker exec -it delivery_service-web-1 python manage.py test product.tests.test_services

from django.test import TestCase
from delivery.enums import DeliveryType
from product.models import Product, UniqueProduct
from product.services import StockService
from seller.models import Shop
from users.models import User


class TestStockService(TestCase):
    """
    Тестирование StockService.

    Проверяется:
    - получение текущего остатка;
    - пополнение склада;
    - запрет пополнения отрицательным/нулевым количеством;
    - списание товара;
    - запрет списания отрицательным/нулевым количеством;
    - запрет списания товара сверх остатка;
    - проверка наличия товара;
    - резервирование товара;
    - запрет резервирования при недостаточном остатке.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test shop",
            carrier=DeliveryType.CDEK,
        )

        self.product = Product.objects.create(
            name="Test product",
            shop=self.shop,
        )

        self.unique_product = UniqueProduct.objects.create(
            product=self.product,
            ware_key="SKU-001",
            price="1000.00",
            color="Красный",
            size="L",
            height=20,
            length=30,
            width=10,
            weight=500,
            stock=10,
        )

    def test_get_stock(self):
        """Возвращает текущий остаток товара."""

        stock = StockService.get_stock(
            self.unique_product,
        )

        self.assertEqual(
            stock,
            10,
        )

    def test_increase_stock(self):
        """Увеличивает остаток товара."""

        result = StockService.increase(
            unique_product=self.unique_product,
            amount=5,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            result,
            self.unique_product,
        )

        self.assertEqual(
            self.unique_product.stock,
            15,
        )

    def test_increase_stock_with_zero_amount(self):
        """Нельзя пополнить склад на ноль."""

        with self.assertRaisesMessage(
            ValueError,
            "Количество для увеличения должно быть больше нуля.",
        ):
            StockService.increase(
                unique_product=self.unique_product,
                amount=0,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    def test_increase_stock_with_negative_amount(self):
        """Нельзя пополнить склад отрицательным количеством."""

        with self.assertRaisesMessage(
            ValueError,
            "Количество для увеличения должно быть больше нуля.",
        ):
            StockService.increase(
                unique_product=self.unique_product,
                amount=-5,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    def test_decrease_stock(self):
        """Уменьшает остаток товара."""

        result = StockService.decrease(
            unique_product=self.unique_product,
            amount=4,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            result,
            self.unique_product,
        )

        self.assertEqual(
            self.unique_product.stock,
            6,
        )

    def test_decrease_stock_with_zero_amount(self):
        """Нельзя списать нулевое количество."""

        with self.assertRaisesMessage(
            ValueError,
            "Количество для уменьшения должно быть больше нуля.",
        ):
            StockService.decrease(
                unique_product=self.unique_product,
                amount=0,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    def test_decrease_stock_with_negative_amount(self):
        """Нельзя списать отрицательное количество."""

        with self.assertRaisesMessage(
            ValueError,
            "Количество для уменьшения должно быть больше нуля.",
        ):
            StockService.decrease(
                unique_product=self.unique_product,
                amount=-3,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    def test_decrease_stock_when_not_enough_stock(self):
        """Нельзя списать больше товара, чем есть на складе."""

        with self.assertRaisesMessage(
            ValueError,
            "Недостаточно товара на складе.",
        ):
            StockService.decrease(
                unique_product=self.unique_product,
                amount=11,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    def test_has_stock(self):
        """Проверяет наличие необходимого количества товара."""

        self.assertTrue(
            StockService.has_stock(
                self.unique_product,
                amount=5,
            )
        )

        self.assertTrue(
            StockService.has_stock(
                self.unique_product,
                amount=10,
            )
        )

        self.assertFalse(
            StockService.has_stock(
                self.unique_product,
                amount=11,
            )
        )

    def test_has_stock_with_zero_amount(self):
        """Для нулевого количества возвращается False."""

        self.assertFalse(
            StockService.has_stock(
                self.unique_product,
                amount=0,
            )
        )

    def test_has_stock_with_negative_amount(self):
        """Для отрицательного количества возвращается False."""

        self.assertFalse(
            StockService.has_stock(
                self.unique_product,
                amount=-1,
            )
        )

    def test_reserve(self):
        """Резервирует необходимое количество товара."""

        result = StockService.reserve(
            unique_product_id=self.unique_product.id,
            amount=4,
        )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            result.id,
            self.unique_product.id,
        )

        self.assertEqual(
            self.unique_product.stock,
            6,
        )

    def test_reserve_when_not_enough_stock(self):
        """Нельзя зарезервировать больше товара, чем есть."""

        with self.assertRaisesMessage(
            ValueError,
            "Недостаточно товара на складе.",
        ):
            StockService.reserve(
                unique_product_id=self.unique_product.id,
                amount=11,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    def test_reserve_with_zero_amount(self):
        """Нельзя резервировать нулевое количество."""

        with self.assertRaisesMessage(
            ValueError,
            "Количество должно быть больше нуля.",
        ):
            StockService.reserve(
                unique_product_id=self.unique_product.id,
                amount=0,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )

    def test_reserve_with_negative_amount(self):
        """Нельзя резервировать отрицательное количество."""

        with self.assertRaisesMessage(
            ValueError,
            "Количество должно быть больше нуля.",
        ):
            StockService.reserve(
                unique_product_id=self.unique_product.id,
                amount=-2,
            )

        self.unique_product.refresh_from_db()

        self.assertEqual(
            self.unique_product.stock,
            10,
        )
