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