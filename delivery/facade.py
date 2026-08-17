"""
Фасад модуля доставки.

Предоставляет единый интерфейс для бизнес-логики маркетплейса.
Скрывает детали работы с конкретными службами доставки:
- выбор адаптера;
- форматирование данных;
- работу с внешним API.

Бизнес-логика заказа не зависит от реализации CDEK, Boxberry,
DHL и других служб доставки.
"""
from delivery.exceptions import DeliveryError
from delivery.factories.delivery import DeliveryFactory
from delivery.schemas.tariffs import ShopDeliveryResultDTO
from order.models import Cart
from seller.models import Shop
from rest_framework.exceptions import ValidationError


class DeliveryFacade:
    """
    Единая точка входа для операций доставки.
    Отвечает за:
    - расчет стоимости доставки;
    - создание отправления;
    - получение статуса;
    - отмену доставки;
    - обработку возвратов.
    """

    def pre_calculate_delivery(
            self,
            user,
            **kwargs,
    ) -> list[ShopDeliveryResultDTO]:
        """Отвечает за:
        - получить корзину;
        - определить магазины;
        - вызвать сервис для каждого магазина;
        - собрать общий list[ShopDeliveryResultDTO]."""

        # Получаем корзину пользователя.
        try:
            cart = user.cart
        except Cart.DoesNotExist:
            return [
                ShopDeliveryResultDTO(
                    shop_id=0,
                    shop_name="",
                    unique_product_ids=[],
                    options=[],
                    error="Корзина не найдена",
                )
            ]

        # проверяем наличие у пользователя города доставки
        if not user.location_to:
            raise ValidationError(
                "У пользователя не указан город доставки"
            )
        # проверяем наличие у пользователя региона доставки
        if not user.location_to_region:
            raise ValidationError(
                "У пользователя не указан регион доставки"
            )
        # Получаем магазины, товары которых есть в корзине.
        shops = (
            Shop.objects
            .filter(
                products__variants__cart_items__cart=cart
            )
            .distinct()
        )

        if not shops.exists():
            return [
                ShopDeliveryResultDTO(
                    shop_id=0,
                    shop_name="",
                    unique_product_ids=[],
                    options=[],
                    error="Корзина пуста",
                )
            ]

        results = []

        # Для каждого магазина отдельно рассчитываем доставку.
        for shop in shops:

            try:
                service = DeliveryFactory.get_service(shop)

                result = service.process(
                    shop=shop,
                    user=user,
                    **kwargs,
                )

            except DeliveryError as exc:
                result = ShopDeliveryResultDTO(
                    shop_id=shop.id,
                    shop_name=shop.name,
                    unique_product_ids=[],
                    options=[],
                    error=str(exc),
                )

            results.append(result)

        return results

    def calculate_delivery(self, **kwargs):
        """
        Расчет стоимости доставки.
        """
        return self.adapter.calculate_delivery(**kwargs)

    def create_delivery(self, **kwargs):
        """
        Регистрация отправления в службе доставки.
        """
        return self.adapter.create_delivery(**kwargs)

    def get_status(self, delivery_id):
        """
        Получение текущего статуса доставки.
        """
        return self.adapter.get_status(delivery_id)

    def cancel_delivery(self, delivery_id):
        """
        Отмена отправления.
        """
        return self.adapter.cancel_delivery(delivery_id)