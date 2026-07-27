from rest_framework import serializers
from .models import Shop

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'owner', 'legal_info']
        read_only_fields = ["owner"]


class ShopDeliverySettingSerializer(serializers.Serializer):
    tariffs = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
