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