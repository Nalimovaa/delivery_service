from rest_framework import serializers
from seller.models import Shop, ShopDeliverySetting
from rest_framework import serializers
from delivery.serializers import CDEKTariffSerializer


class ShopSerializer(serializers.ModelSerializer):
    """Сериалайзрк для CRUD магазина"""
    class Meta:
        model = Shop
        fields = ['id', 'name', 'owner', 'legal_info',  "location_from", "carrier",]
        read_only_fields = ["owner"]


class ShopDeliverySettingSerializer(serializers.Serializer):
    """Для передачи списка кодов тарифов для сохранения в ЛК продавца"""
    tariffs = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )


class ShopDeliverySettingReadSerializer(
    serializers.ModelSerializer
):
    """ Serializer для просмотра настроек кодов тарифов СДЕКа в ЛК продавца"""

    tariff = CDEKTariffSerializer()


    class Meta:
        model = ShopDeliverySetting

        fields = (
            "id",
            "tariff",
            "created_at",
        )
