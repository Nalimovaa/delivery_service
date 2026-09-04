from seller.models import Shop, CDEKShopDeliverySetting, SellerRequest
from rest_framework import serializers
from delivery.serializers import CDEKTariffSerializer
from users.services import normalize_phone


class ShopSerializer(serializers.ModelSerializer):
    """Сериалайзер для CRUD магазина."""

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "owner",
            "legal_info",
            "location_from",
            "location_from_region",
            "location_from_district",
            "location_from_country",
            "address",
            "postal_code",
            "phone",
            "carrier",
        ]
        read_only_fields = ["owner"]

    def validate_phone(self, value):
        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))



class ShopDeliverySettingSerializer(serializers.Serializer):
    """Для передачи списка кодов тарифов для сохранения в ЛК продавца"""
    tariffs = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )


class CDEKShopDeliverySettingReadSerializer(
    serializers.ModelSerializer
):
    """ Serializer для просмотра настроек кодов тарифов СДЕКа в ЛК продавца"""

    tariff = CDEKTariffSerializer()


    class Meta:
        model = CDEKShopDeliverySetting

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