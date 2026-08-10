from django.db import transaction

from product.models import UniqueProduct


class StockService:

    @staticmethod
    def get_stock(unique_product: UniqueProduct) -> int:
        """
        Возвращает текущий остаток товара.
        """
        return unique_product.stock

    @staticmethod
    @transaction.atomic
    def increase(
        unique_product: UniqueProduct,
        amount: int,
    ) -> UniqueProduct:
        """
        Увеличивает остаток товара на складе.
        """

        if amount <= 0:
            raise ValueError(
                "Количество для увеличения должно быть больше нуля."
            )

        unique_product.stock += amount
        unique_product.save(
            update_fields=["stock"],
        )

        return unique_product

    @staticmethod
    @transaction.atomic
    def decrease(
        unique_product: UniqueProduct,
        amount: int,
    ) -> UniqueProduct:
        """
        Уменьшает остаток товара на складе.
        """

        if amount <= 0:
            raise ValueError(
                "Количество для уменьшения должно быть больше нуля."
            )

        if unique_product.stock < amount:
            raise ValueError(
                "Недостаточно товара на складе."
            )

        unique_product.stock -= amount
        unique_product.save(
            update_fields=["stock"],
        )

        return unique_product

    @staticmethod
    def has_stock(
        unique_product: UniqueProduct,
        amount: int = 1,
    ) -> bool:
        """
        Проверяет наличие необходимого количества товара.
        """

        if amount <= 0:
            return False

        return unique_product.stock >= amount

    @staticmethod
    @transaction.atomic
    def reserve(
            unique_product_id: int,
            amount: int,
    ) -> UniqueProduct:
        """
        Резервирует товар на складе для заказа.
        """

        if amount <= 0:
            raise ValueError(
                "Количество должно быть больше нуля."
            )

        unique_product = (
            UniqueProduct.objects
            .select_for_update()
            .get(id=unique_product_id)
        )

        if unique_product.stock < amount:
            raise ValueError(
                "Недостаточно товара на складе."
            )

        unique_product.stock -= amount

        unique_product.save(
            update_fields=["stock"],
        )

        return unique_product