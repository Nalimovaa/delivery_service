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
from delivery.factories.delivery import DeliveryFactory
from delivery.services.tariffs import DeliveryOptionsService
from order.models import Cart, CartItem
from seller.models import Shop, ShopDeliverySetting
from django.db.models import Prefetch
from typing import List, Dict, Any
from collections import defaultdict


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

    def pre_calculate_delivery(self, user, **kwargs) -> List[Dict[str, Any]]:
        """
        Предварительный расчёт доставки для всех магазинов в корзине пользователя.
        """
        try:
            cart = user.cart
        except Cart.DoesNotExist:
            return [{"error": "Корзина не найдена"}]

        cart_items = CartItem.objects.filter(cart=cart).select_related(
            'unique_product__product__shop'
        ).prefetch_related(
            Prefetch(
                'unique_product__product__shop__delivery_settings',
                queryset=ShopDeliverySetting.objects.select_related('tariff')
            )
        )

        if not cart_items.exists():
            return [{"error": "Корзина пуста"}]

        # Группировка по магазинам
        grouped_by_shop = defaultdict(list)
        for item in cart_items:
            shop = item.unique_product.product.shop
            grouped_by_shop[shop].append(item)

        # Проверка наличия города у пользователя
        if not user.location_to:
            return [{"error": "У пользователя не указан город доставки"}]

        results = []
        for shop, items in grouped_by_shop.items():
            # Агрегируем габариты и вес
            total_weight = 0
            max_height = max_length = max_width = 0
            unique_product_ids = []
            for item in items:
                unique_product_ids.append(item.unique_product.id)
                total_weight += item.unique_product.weight * item.amount
                max_height = max(max_height, item.unique_product.height)
                max_length = max(max_length, item.unique_product.length)
                max_width = max(max_width, item.unique_product.width)

            # Проверка города отправления
            if not shop.location_from:
                results.append({
                    'shop_id': shop.id,
                    'shop_name': shop.name,
                    'unique_product_ids': unique_product_ids,
                    'options': [],
                    'error': 'У магазина не указан город отправления'
                })
                continue

            # Проверка настроек тарифов
            if not shop.delivery_settings.exists():
                results.append({
                    'shop_id': shop.id,
                    'shop_name': shop.name,
                    'unique_product_ids': unique_product_ids,
                    'options': [],
                    'error': 'У магазина не настроены тарифы доставки'
                })
                continue

            # Получаем адаптер через фабрику
            try:
                adapter = DeliveryFactory.get_adapter(shop)
            except NotImplementedError as e:
                results.append({
                    'shop_id': shop.id,
                    'shop_name': shop.name,
                    'unique_product_ids': unique_product_ids,
                    'options': [],
                    'error': str(e)
                })
                continue

            # Вызываем адаптер
            try:
                response = adapter.pre_calculate_delivery(
                    from_location_code=int(shop.location_from),
                    to_location_code=int(user.location_to),
                    height=max_height,
                    length=max_length,
                    weight=total_weight,
                    width=max_width,
                    services=kwargs.get('services'),
                    currency=kwargs.get('currency', 'RUB'),
                    date=kwargs.get('date'),
                    additional_order_types=kwargs.get('additional_order_types'),
                    shipment_point=kwargs.get('shipment_point'),
                    delivery_point=kwargs.get('delivery_point'),
                )
            except Exception as e:
                results.append({
                    'shop_id': shop.id,
                    'shop_name': shop.name,
                    'unique_product_ids': unique_product_ids,
                    'options': [],
                    'error': f'Ошибка расчёта: {str(e)}'
                })
                continue

            # Обработка ответа через сервис
            options = DeliveryOptionsService.process_cdek_response(shop, response)

            results.append({
                'shop_id': shop.id,
                'shop_name': shop.name,
                'unique_product_ids': unique_product_ids,
                'options': options,
                'error': None,
            })

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