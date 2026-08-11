from rest_framework import serializers
from seller.models import Shop, ShopDeliverySetting, SellerRequest
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


class SellerRequestSerializer(serializers.ModelSerializer):
    """ Serializer для просмотра заявок на получение роли Seller в ЛК пользователя"""
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = SellerRequest
        fields = (
            "id",
            "user",
            "user_email",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "user_email",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        )



class SellerRequestRejectSerializer(serializers.Serializer):
    """ Serializer для отклонения заявки на получение роли Seller в ЛК пользователя"""
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=2000,
    )