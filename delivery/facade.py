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
from delivery.schemas.tariffs import ShopDeliveryResultDTO, CartDeliveryResultDTO, ShopCalculateDeliveryResultDTO
from decimal import Decimal
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
                    carrier_name="",
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
                    carrier_name=shop.get_carrier_display(),
                    unique_product_ids=[],
                    options=[],
                    error=str(exc),
                )

            results.append(result)

        return results

    def calculate_delivery(
            self,
            user,
            selected_tariffs: dict[int, int],
            **kwargs,
    ) -> CartDeliveryResultDTO:
        """Расчет стоимости доставки для корзины пользователя."""

        # Получаем корзину пользователя.
        try:
            cart = user.cart
        except Cart.DoesNotExist:
            return CartDeliveryResultDTO(
                shops=[],
                products_sum=None,
                delivery_sum=None,
                total_sum=None,
                error="Корзина не найдена",
            )

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
            return CartDeliveryResultDTO(
                shops=[],
                products_sum=None,
                delivery_sum=None,
                total_sum=None,
                error="Корзина пуста",
            )

        results = []

        total_products_sum = Decimal("0")
        total_delivery_sum = Decimal("0")

        # Для каждого магазина отдельно рассчитываем доставку.
        for shop in shops:

            # Получаем выбранный пользователем тариф
            # для конкретного магазина.
            tariff_code = selected_tariffs.get(shop.id)

            if tariff_code is None:
                results.append(
                    ShopCalculateDeliveryResultDTO(
                        shop_id=shop.id,
                        shop_name=shop.name,
                        carrier_name=shop.get_carrier_display(),
                        unique_product_ids=[],
                        products_sum=None,
                        delivery_sum=None,
                        total_sum=None,
                        error="Для магазина не выбран тариф доставки",
                    )
                )
                continue

            try:
                # Получаем сервис расчета по коду тарифа для транспортной компании магазина.
                service = DeliveryFactory.get_code_tariff_service(shop)

                result = service.process(
                    shop=shop,
                    user=user,
                    tariff_code=tariff_code,
                    **kwargs,
                )

            except DeliveryError as exc:
                results.append(
                    ShopCalculateDeliveryResultDTO(
                        shop_id=shop.id,
                        shop_name=shop.name,
                        carrier_name=shop.get_carrier_display(),
                        unique_product_ids=[],
                        products_sum=None,
                        delivery_sum=None,
                        total_sum=None,
                        tariff_code=tariff_code,
                        error=str(exc),
                    )
                )
                continue

            total_sum = (
                result.products_sum + result.delivery_sum
                if result.products_sum is not None
                   and result.delivery_sum is not None
                else None
            )

            shop_result = ShopCalculateDeliveryResultDTO(
                shop_id=result.shop_id,
                shop_name=result.shop_name,
                carrier_name=shop.get_carrier_display(),
                unique_product_ids=result.unique_product_ids,
                products_sum=result.products_sum,
                delivery_sum=result.delivery_sum,
                total_sum=total_sum,
                tariff_code=result.tariff_code,
                tariff_name=result.tariff_name,
                calculation=result.calculation,
                error=result.error,
            )

            results.append(shop_result)

            if result.products_sum is not None:
                total_products_sum += result.products_sum

            if result.delivery_sum is not None:
                total_delivery_sum += result.delivery_sum

        return CartDeliveryResultDTO(
            shops=results,
            products_sum=total_products_sum,
            delivery_sum=total_delivery_sum,
            total_sum=total_products_sum + total_delivery_sum,
        )

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