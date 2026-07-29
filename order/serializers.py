from rest_framework import serializers
from .models import Order, OrderProduct

class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        fields = (
            "unique_product",
            "amount",
            "price",
            "product_name",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderProductSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "owner",
            "created_at",
            "items",
        )

