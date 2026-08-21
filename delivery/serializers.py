from rest_framework import serializers


class CDEKTariffSerializer(serializers.Serializer):
    """ Сериализатор для получени всех тарифов по договору продавца.
     is_active здесь не нужен, в Redis кладем только активные тарифы. """

    tariff_code = serializers.IntegerField()
    tariff_name = serializers.CharField()

    delivery_mode = serializers.IntegerField()
    delivery_mode_name = serializers.CharField()

    weight_min = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    weight_max = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    length_max = serializers.IntegerField()
    width_max = serializers.IntegerField()
    height_max = serializers.IntegerField()



# Сериалайзеры для предварительного расчета стоимости доставки товаров в корзине пользователя (СДЭК) - ответ от DeliveryFacade.pre_calculate_delivery()

class DeliveryDateRangeSerializer(serializers.Serializer):
    min = serializers.CharField()
    max = serializers.CharField()


class DeliveryServiceSerializer(serializers.Serializer):
    code = serializers.CharField()
    sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )


class DeliveryOptionSerializer(serializers.Serializer):
    tariff_code = serializers.IntegerField()
    tariff_name = serializers.CharField()
    delivery_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    period_min = serializers.IntegerField()
    period_max = serializers.IntegerField()

    delivery_date_range = DeliveryDateRangeSerializer(
        allow_null=True,
        required=False,
    )

    services = DeliveryServiceSerializer(
        many=True,
        required=False,
    )

    total_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = serializers.CharField()


class ShopDeliveryResultSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    shop_name = serializers.CharField()
    carrier_name = serializers.CharField()

    unique_product_ids = serializers.ListField(
        child=serializers.IntegerField(),
    )

    options = DeliveryOptionSerializer(
        many=True,
    )

    error = serializers.CharField(
        allow_null=True,
        required=False,
    )


class CalculateDeliveryRequestSerializer(serializers.Serializer):
    selected_tariffs = serializers.DictField(
        child=serializers.IntegerField(),
        help_text=(
            "Соответствие ID магазина выбранному коду тарифа. "
            "Например: {\"1\": 137, \"4\": 121}"
        ),
    )

    def validate_selected_tariffs(self, value):
        selected_tariffs = {}

        for shop_id, tariff_code in value.items():

            if not shop_id:
                raise serializers.ValidationError(
                    "ID магазина не может быть пустым."
                )

            try:
                shop_id = int(shop_id)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    f"Некорректный ID магазина: {shop_id!r}. "
                    "ID магазина должен быть целым числом."
                )

            if shop_id <= 0:
                raise serializers.ValidationError(
                    "ID магазина должен быть положительным целым числом."
                )

            if tariff_code <= 0:
                raise serializers.ValidationError(
                    f"Некорректный код тарифа для магазина {shop_id}. "
                    "Код тарифа должен быть положительным целым числом."
                )

            selected_tariffs[shop_id] = tariff_code

        return selected_tariffs

# Сериалайзеры для расчета стоимости доставки по коду тарифа (СДЭК) - для сваггера

class ShopCalculateDeliveryResultSerializer(serializers.Serializer):
    """Ответ по расчету доставки для одного магазина."""

    shop_id = serializers.IntegerField()
    shop_name = serializers.CharField()
    carrier_name = serializers.CharField()
    unique_product_ids = serializers.ListField(
        child=serializers.IntegerField(),
    )

    products_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    delivery_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    total_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )

    tariff_code = serializers.IntegerField(
        allow_null=True,
        required=False,
    )
    tariff_name = serializers.CharField(
        allow_null=True,
        required=False,
    )

    calculation = serializers.JSONField(
        allow_null=True,
        required=False,
    )

    error = serializers.CharField(
        allow_null=True,
        required=False,
    )


class CartDeliveryResultSerializer(serializers.Serializer):
    """Итоговый результат расчета стоимости всей корзины."""

    shops = ShopCalculateDeliveryResultSerializer(
        many=True,
    )

    products_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    delivery_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    total_sum = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )

    error = serializers.CharField(
        allow_null=True,
        required=False,
    )


# Сериалайзер для получения списка ПВЗ СДЭКа

class CDEKDeliveryPointSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    uuid = serializers.UUIDField()

    type = serializers.CharField()
    owner_code = serializers.CharField()

    status = serializers.CharField()

    is_handout = serializers.BooleanField()
    is_reception = serializers.BooleanField()
    allowed_cod = serializers.BooleanField()

    country_code = serializers.CharField()
    region_code = serializers.IntegerField()
    region = serializers.CharField()

    city_code = serializers.IntegerField()
    city = serializers.CharField()

    postal_code = serializers.CharField(
        allow_null=True,
        required=False,
    )

    address = serializers.CharField(
        allow_null=True,
        required=False,
    )

    address_full = serializers.CharField(
        allow_null=True,
        required=False,
    )

    longitude = serializers.FloatField(
        allow_null=True,
        required=False,
    )

    latitude = serializers.FloatField(
        allow_null=True,
        required=False,
    )

    city_uuid = serializers.UUIDField()