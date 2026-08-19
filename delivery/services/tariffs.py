from django.core.cache import cache
from delivery.adapters.cdek import CDEKAdapter
from delivery.models import CDEKTariff
from delivery.schemas.tariffs import AvailableTariffsResponseSchema, TariffListResponseSchema, DeliveryOptionDTO, \
    DeliveryDateRangeDTO, ShopDeliveryResultDTO, CDEKLocationResultDTO, CalculateDeliveryResultDTO
from order.models import CartItem
from seller.models import Shop, ShopDeliverySetting
from django.db.models import Prefetch


class CDEKTariffService:
    CACHE_KEY = "cdek:tariffs"
    CACHE_TIMEOUT = 60 * 60 * 24

    def fetch_tariffs(self) -> AvailableTariffsResponseSchema:
        """ Получение списка тарифов из API СДЭК. """
        adapter = CDEKAdapter()
        return adapter.get_all_tariffs()

    def prepare_tariffs(
            self,
            response: AvailableTariffsResponseSchema
    ):
        """ Генератор подготовленных данных для сохранения в БД. """

        for tariff in response.tariff_codes:

            for mode in tariff.delivery_modes:

                if mode.tariff_code is None:
                    continue

                yield {
                    "tariff_code": mode.tariff_code,
                    "tariff_name": tariff.tariff_name,
                    "delivery_mode": mode.delivery_mode,
                    "delivery_mode_name": mode.delivery_mode_name,
                    "weight_min": tariff.weight_min,
                    "weight_max": tariff.weight_max,
                    "length_max": tariff.length_max,
                    "width_max": tariff.width_max,
                    "height_max": tariff.height_max,
                    "is_active": True,
                }

    def save_tariffs(self, tariffs):
        """ Массовое сохранение и обновление тарифов. """
        CDEKTariff.objects.bulk_update_or_create(tariffs)

    def deactivate_missing(self, active_tariff_codes):
        """ Деактивация тарифов, отсутствующих в новом ответе API. """
        CDEKTariff.objects.exclude(
            tariff_code__in=active_tariff_codes
        ).update(is_active=False)

    def update_cache(self):
        """ Кэширование актуальных тарифов. """
        cache.set(
            self.CACHE_KEY,
            list(
                CDEKTariff.objects.filter(
                    is_active=True
                ).values(
                    "tariff_code",
                    "tariff_name",
                    "delivery_mode",
                    "delivery_mode_name",
                    "weight_min",
                    "weight_max",
                    "length_max",
                    "width_max",
                    "height_max",
                )
            ),
            timeout=self.CACHE_TIMEOUT,
        )

    def sync_cdek_tariffs(self):
        """ Полная синхронизация тарифов. """
        response = self.fetch_tariffs() # Получение данных из API СДЭК

        tariffs = list(self.prepare_tariffs(response)) # Подготовка данных для сохранения в БД

        active_codes = {
            tariff["tariff_code"] # итерируемся по каждому тарифу из API СДЭКа
            for tariff in tariffs
        }

        self.save_tariffs(tariffs) # Сохранение тарифов в БД из API СДЭК

        self.deactivate_missing(active_codes) # Деактивация тарифов в БД, отсутствующих в новом ответе API

        self.update_cache() # Обновление кэша с актуальными тарифами

        return {
            "processed": len(tariffs),
        }

    def get_cached_tariffs(self):
        """ Получение всех актуальных тарифов по договору продавца из Redis. """
        return cache.get(self.CACHE_KEY, [])


class CDEKLocationService:

    def __init__(self, adapter: CDEKAdapter | None = None):
        self.adapter = adapter or CDEKAdapter()

    def get_location_code(
        self,
        *,
        city: str,
        region: str,
        district: str | None = None,
    ) -> int:
        cities = self.adapter.suggest_cities(
            name=city,
            country_code="RU",
        )

        # Сначала фильтруем по региону
        cities = [
            city_data
            for city_data in cities
            if region.lower() in city_data.full_name.lower()
        ]

        # Если по региону найдено несколько вариантов,
        # дополнительно фильтруем по району
        if len(cities) > 1 and district:
            cities = [
                city_data
                for city_data in cities
                if district.lower() in city_data.full_name.lower()
            ]

        if len(cities) != 1:
            return CDEKLocationResultDTO(
                error=(
                    f"Не удалось однозначно определить "
                    f"населенный пункт: {city}, {region}"
                )
            )

        # ответ: code=430 error=None
        return CDEKLocationResultDTO(
            code=cities[0].code,
        )

class CDEKDeliveryOptionsService:
    """Обрабатывает ответы от API СДЭКа по предварительной стоимости доставки.
    Отвечает за:
    - получить CartItem конкретного магазина;
    - определить город магазина;
    - получить CDEK-коды;
    - вызвать CDEKAdapter;
    - получить тарифы;
    - отфильтровать тарифы;
    - вернуть ShopDeliveryResultDTO."""

    def __init__(self):
        self.adapter = CDEKAdapter()
        self.location_service = CDEKLocationService()

    def process(
        self,
        shop,
        user,
        **kwargs,
    ) -> ShopDeliveryResultDTO:

        # Загружаем позиции корзины для данного пользователя и магазина
        items = list(
            CartItem.objects
            .filter(cart=user.cart)
            .select_related(
                "unique_product",
                "unique_product__product",
                "unique_product__product__shop",
            )
            .prefetch_related(
                Prefetch(
                    "unique_product__product__shop__delivery_settings",
                    queryset=ShopDeliverySetting.objects.select_related("tariff"),
                )
            )
        )

        if not items:
            return ShopDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name="",
                unique_product_ids=[],
                options=[],
                error="В корзине нет товаров этого магазина",
            )

        # получаем список id уникальных продуктов для магазина
        unique_product_ids = [
            item.unique_product_id
            for item in items
        ]

        # получаем название службы доставки магазина
        carrier_name = shop.get_carrier_display()

        # проверяем наличие у магазина города отправления
        if not shop.location_from:
            return ShopDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                unique_product_ids=unique_product_ids,
                options=[],
                error="У магазина не указан город отправления",
            )
        # проверяем наличие у магазина региона отправления
        if not shop.location_from_region:
            return ShopDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                unique_product_ids=unique_product_ids,
                options=[],
                error="У магазина не указан регион отправления",
            )

        # получаем CDEK-коды:
        from_location_result = self.location_service.get_location_code(
            city=shop.location_from,
            region=shop.location_from_region,
            district=shop.location_from_district,
        )

        if from_location_result.error:
            return ShopDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                unique_product_ids=unique_product_ids,
                options=[],
                error=from_location_result.error,
            )

        to_location_result = self.location_service.get_location_code(
            city=user.location_to,
            region=user.location_to_region,
            district=user.location_to_district,
        )

        if to_location_result.error:
            return ShopDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                unique_product_ids=unique_product_ids,
                options=[],
                error=to_location_result.error,
            )

        # проверяем наличие у магазина настроенных тарифов доставки
        delivery_settings = list(
            shop.delivery_settings.all()
        )

        if not delivery_settings:
            return ShopDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                unique_product_ids=unique_product_ids,
                options=[],
                error="У магазина не настроены тарифы доставки",
            )

        # Подготавливаем данные в формате,
        # необходимом CDEKAdapter.
        data = self._prepare_data(
            **kwargs,
        )

        # Адаптер выполняет запрос к API СДЭК.
        response = self.adapter.pre_calculate_delivery(
            from_location_code=from_location_result.code,
            to_location_code=to_location_result.code,
            items=items,
            **data,
        )
        # Фильтруем полученные тарифы по настройкам магазина.
        options = self._filter_tariffs(
            shop=shop,
            response=response,
        )

        if not options:
            return ShopDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                unique_product_ids=unique_product_ids,
                options=[],
                error="Для магазина нет доступных тарифов доставки",
            )

        return ShopDeliveryResultDTO(
            shop_id=shop.id,
            shop_name=shop.name,
            carrier_name=carrier_name,
            unique_product_ids=unique_product_ids,
            options=options,
        )

    def _prepare_data(
            self,
            **kwargs,
    ) -> dict:
        return {
            "services": kwargs.get("services"),
            "additional_order_types": kwargs.get(
                "additional_order_types"
            ),
            "shipment_point": kwargs.get(
                "shipment_point"
            ),
            "delivery_point": kwargs.get(
                "delivery_point"
            ),
            "currency": kwargs.get(
                "currency"
            ),
            "date": kwargs.get("date"),
        }

    def _filter_tariffs(
            self,
            shop,
            response: TariffListResponseSchema,
    ) -> list[dict]:
        """Фильтрует тарифы CDEK по настройкам доставки магазина."""

        # Коды тарифов, которые разрешены в настройках магазина: allowed_codes = {121, 59}
        allowed_codes = {
            setting.tariff.tariff_code
            for setting in shop.delivery_settings.all()
        }

        # Названия тарифов из БД: {121: "Экономичная посылка", 59: "Посылка склад-склад"}
        tariff_names = {
            tariff.tariff_code: tariff.tariff_name
            for tariff in CDEKTariff.objects.filter(
                tariff_code__in=allowed_codes
            )
        }

        options = []

        # список доступных кодов тарифов из ответа API СДЕКа
        for tariff_item in response.tariff_codes:
            code = int(tariff_item.tariff_code)  # [121, 59, 136]

            # Оставляем только тарифы,
            # которые разрешены настройками магазина.
            if code not in allowed_codes: # code = [121, 59, 136] сравниваем с allowed_codes = {121, 59}
                continue

            # tariff_item — это один объект TariffItemSchema
            # а tariff_item.result - это объект TariffResultSchema, содержащий информацию о стоимости и сроках доставки для данного тарифа из API СДЕКа
            result = tariff_item.result

            options.append({
                "tariff_code": code,
                "tariff_name": tariff_names.get(
                    code,
                    f"Тариф {code}",
                ),
                "delivery_sum": result.delivery_sum,
                "period_min": result.period_min,
                "period_max": result.period_max,
                "delivery_date_range": (
                    result.delivery_date_range.model_dump()
                    if result.delivery_date_range
                    else None
                ),
                "services": [
                    {
                        "code": service.code,
                        "sum": service.sum,
                    }
                    for service in result.services
                ],
                "total_sum": result.total_sum,
                "currency": result.currency,
            })

        return options



class CDEKCalculateDeliveryService:
    """
    Выполняет расчет доставки по конкретному тарифу CDEK.

    Отвечает за:
    - получение CartItem конкретного магазина;
    - определение города отправления магазина;
    - определение города получения пользователя;
    - получение CDEK-кодов городов;
    - проверку наличия тарифов в настройках магазина;
    - проверку наличия переданного пользователем тарифа
      в настройках магазина;
    - вызов CDEKAdapter.calculate_delivery();
    - преобразование ответа CDEK в CalculateDeliveryResultDTO.
    """

    def __init__(self):
        self.adapter = CDEKAdapter()
        self.location_service = CDEKLocationService()

    def process(
        self,
        shop,
        user,
        tariff_code: int,
        **kwargs,
    ) -> CalculateDeliveryResultDTO:

        # 1. Получаем товары корзины данного магазина
        items = list(
            CartItem.objects
            .filter(
                cart=user.cart,
                unique_product__product__shop=shop,
            )
            .select_related(
                "unique_product",
                "unique_product__product",
                "unique_product__product__shop",
            )
            .prefetch_related(
                Prefetch(
                    "unique_product__product__shop__delivery_settings",
                    queryset=ShopDeliverySetting.objects.select_related(
                        "tariff"
                    ),
                )
            )
        )

        if not items:
            return CalculateDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name="",
                tariff_code=tariff_code,
                unique_product_ids=[],
                products_sum=None,
                delivery_sum=None,
                error="В корзине нет товаров этого магазина",
            )

        # получаем список id уникальных продуктов для магазина
        unique_product_ids = [
            item.unique_product_id
            for item in items
        ]

        # получаем название службы доставки магазина
        carrier_name = shop.get_carrier_display()

        # сумма товаров в корзине для данного магазина
        products_sum = sum(
            item.unique_product.price * item.amount
            for item in items
        )

        # 2. Проверяем город отправления магазина
        if not shop.location_from:
            return CalculateDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                tariff_code=tariff_code,
                unique_product_ids=unique_product_ids,
                products_sum=products_sum,
                delivery_sum=None,
                error="У магазина не указан город отправления",
            )

        if not shop.location_from_region:
            return CalculateDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                tariff_code=tariff_code,
                unique_product_ids=unique_product_ids,
                products_sum=products_sum,
                delivery_sum=None,
                error="У магазина не указан регион отправления",
            )
        # 3. Получаем CDEK-код города отправления
        from_location_result = self.location_service.get_location_code(
            city=shop.location_from,
            region=shop.location_from_region,
            district=shop.location_from_district,
        )

        if from_location_result.error:
            return CalculateDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                tariff_code=tariff_code,
                unique_product_ids=unique_product_ids,
                products_sum=products_sum,
                delivery_sum=None,
                error=from_location_result.error,
            )

        # 4. Получаем CDEK-код города пользователя
        to_location_result = self.location_service.get_location_code(
            city=user.location_to,
            region=user.location_to_region,
            district=user.location_to_district,
        )

        if to_location_result.error:
            return CalculateDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                tariff_code=tariff_code,
                unique_product_ids=unique_product_ids,
                products_sum=products_sum,
                delivery_sum=None,
                error=to_location_result.error,
            )

        # 5. Получаем настройки доставки магазина
        delivery_settings = list(
            shop.delivery_settings.select_related("tariff")
        )

        if not delivery_settings:
            return CalculateDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                tariff_code=tariff_code,
                unique_product_ids=unique_product_ids,
                products_sum=products_sum,
                delivery_sum=None,
                error="У магазина не настроены тарифы доставки",
            )

        # 6. Проверяем, что выбранный тариф разрешен магазином
        selected_setting = next(
            (
                setting
                for setting in delivery_settings
                if setting.tariff.tariff_code == tariff_code
            ),
            None,
        )

        if selected_setting is None:
            return CalculateDeliveryResultDTO(
                shop_id=shop.id,
                shop_name=shop.name,
                carrier_name=carrier_name,
                tariff_code=tariff_code,
                unique_product_ids=unique_product_ids,
                products_sum=products_sum,
                delivery_sum=None,
                error=(
                    f"Тариф {tariff_code} "
                    f"не разрешен настройками магазина"
                ),
            )

        # 7. Подготавливаем дополнительные параметры
        data = self._prepare_data(
            **kwargs,
        )

        # 8. Выполняем расчет доставки через CDEK
        response = self.adapter.calculate_delivery(
            from_location_code=from_location_result.code,
            to_location_code=to_location_result.code,
            tariff_code=tariff_code,
            items=items,
            **data,
        )

        # 9. Возвращаем результат
        return CalculateDeliveryResultDTO(
            shop_id=shop.id,
            shop_name=shop.name,
            carrier_name=carrier_name,
            unique_product_ids=unique_product_ids,
            tariff_code=tariff_code,
            tariff_name=selected_setting.tariff.tariff_name,
            products_sum=products_sum,
            delivery_sum=response.total_sum,
            calculation=response,
        )

    def _prepare_data(
        self,
        **kwargs,
    ) -> dict:
        return {
            "services": kwargs.get("services"),
            "additional_order_types": kwargs.get(
                "additional_order_types"
            ),
            "shipment_point": kwargs.get(
                "shipment_point"
            ),
            "delivery_point": kwargs.get(
                "delivery_point"
            ),
            "currency": kwargs.get(
                "currency"
            ),
            "date": kwargs.get("date"),
        }
