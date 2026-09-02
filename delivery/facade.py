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
from delivery.models import OrderDelivery
from delivery.schemas.tariffs import ShopDeliveryResultDTO, CartDeliveryResultDTO, ShopCalculateDeliveryResultDTO
from decimal import Decimal
from order.models import Cart, CartItem, Order, OrderProduct
from product.models import UniqueProduct
from product.services import StockService
from seller.models import Shop
from rest_framework.exceptions import ValidationError
from django.db import transaction


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
                    carrier_name="",
                    unique_product_ids=[],
                    options=[],
                    error="Корзина пуста"
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
                delivery_mode=result.delivery_mode,
                delivery_mode_name=result.delivery_mode_name,
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

    @transaction.atomic
    def create_order(
            self,
            user,
            selected_tariffs: dict[int, int],
            delivery_data: dict[int, dict],
            **kwargs,
    ):
        """
        Создает заказ пользователя и регистрирует его
        в соответствующих транспортных компаниях.

        Этапы:
        1. Получение корзины.
        2. Получение товаров корзины.
        3. Блокировка UniqueProduct.
        4. Проверка остатков.
        5. Повторный расчет доставки.
        6. Создание Order.
        7. Создание OrderProduct.
        8. Создание OrderDelivery для каждого магазина.
        9. Передача отправления в сервис соответствующей ТК.

        {
            "selected_tariffs": {
                "1": 137,
                "4": 121
            },
            "delivery_data": {
                "1": {
                    "address_to": "ул. Стара Загора, д. 130",
                    "postal_code_to": "443114"
                },
                "4": {
                    "delivery_point": "SAM12"
                }
            }
        }

        """

        # 1. Получаем корзину пользователя.
        try:
            cart = user.cart
        except Cart.DoesNotExist:
            raise ValidationError(
                "Корзина пользователя не найдена."
            )

        # 2. Получаем товары корзины.
        cart_items = list(
            CartItem.objects
            .filter(cart=cart)
            .select_related(
                "unique_product",
                "unique_product__product",
                "unique_product__product__shop",
            )
        )

        if not cart_items:
            raise ValidationError(
                "Корзина пуста."
            )

        # 3. Блокируем UniqueProduct: именно строки UniqueProduct, а не CartItem.
        unique_product_ids = {
            item.unique_product_id
            for item in cart_items
        }

        locked_products = {
            product.id: product
            for product in (
                UniqueProduct.objects
                .select_for_update()
                .filter(id__in=unique_product_ids)
            )
        }

        # 4. Проверяем остатки.
        for item in cart_items:
            unique_product = locked_products.get(
                item.unique_product_id
            )

            if unique_product is None:
                raise ValidationError(
                    f"Товар с id={item.unique_product_id} не найден."
                )

            if item.amount <= 0:
                raise ValidationError(
                    f"Некорректное количество товара "
                    f"«{unique_product}»."
                )

            if not StockService.has_stock(
                    unique_product=unique_product,
                    amount=item.amount,
            ):
                raise ValidationError(
                    f"Недостаточно товара "
                    f"«{unique_product}» на складе."
                )

        # 5. Повторно рассчитываем доставку.
        delivery_result = self.calculate_delivery(
            user=user,
            selected_tariffs=selected_tariffs,
            **kwargs,
        )

        if delivery_result.error:
            raise ValidationError(
                delivery_result.error
            )

        for shop_result in delivery_result.shops:
            if shop_result.error:
                raise ValidationError(
                    f"Ошибка доставки для магазина "
                    f"«{shop_result.shop_name}»: "
                    f"{shop_result.error}"
                )

        # 6. Создаем Order.
        order = Order.objects.create(
            owner=user,
        )

        # 7. Создаем OrderProduct.
        order_products = []

        for item in cart_items:
            unique_product = locked_products[
                item.unique_product_id
            ]

            order_product = OrderProduct.objects.create(
                order=order,
                unique_product=unique_product,
                amount=item.amount,
                price=unique_product.price,
                product_name=str(unique_product),
            )

            order_products.append(order_product)

        # 8. Создаем OrderDelivery
        # и передаем отправление соответствующей ТК.
        shops = {
            item.unique_product.product.shop.id:
                item.unique_product.product.shop
            for item in cart_items
        }
        for shop_result in delivery_result.shops:
            shop = shops.get(shop_result.shop_id)
            if shop is None:
                raise ValidationError(
                    f"Магазин с id={shop_result.shop_id} "
                    f"не найден в корзине."
                )

            # Повторно проверяем данные магазина в соответствии с выбранной ТК.
            DeliveryFactory.validate(shop)

            order_delivery = OrderDelivery.objects.create(
                order=order,
                shop=shop,
                delivery_type=shop.carrier,
            )

            shop_delivery_data = delivery_data.get(
                shop_result.shop_id
            )

            if shop_delivery_data is None:
                raise ValidationError(
                    {
                        "delivery_data": (
                            f"Не указаны данные доставки "
                            f"для магазина «{shop.name}»."
                        )
                    }
                )

            # 9. Передаем создание специфичных данных конкретной транспортной компании.
            order_service = DeliveryFactory.get_order_service(shop, user)

            order_service._create_cdek_delivery(
                order_delivery=order_delivery,
                shop_result=shop_result,
                delivery_data=shop_delivery_data
            )

    def get_status(self, delivery_id):
        """
        Получение текущего статуса доставки.
        """
        raise NotImplementedError

    def cancel_delivery(self, delivery_id):
        """
        Отмена отправления.
        """
        raise NotImplementedError