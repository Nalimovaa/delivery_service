from rest_framework import serializers

from delivery.models import CdekDeliveryStatusHistory, CdekDelivery, OrderDelivery
from .models import Order, OrderProduct, ReturnRequest


# Сериалайзеры для создания заказов на перевозку во внешних системах

class CreateOrderRequestSerializer(serializers.Serializer):
    """
    Serializer for creating an order request.

    {
    "selected_tariffs": {
        "1": 139,
        "4": 137
    },
    "delivery_data": {
        "1": {
            "address_to": "ул. Кооперативная, д. 102А",
            "postal_code_to": "446370"
        },
        "4": {
            "address_to": "ул. Кооперативная, д. 102А",
            "postal_code_to": "446370"
        }
    }
}
    """
    selected_tariffs = serializers.DictField(
        child=serializers.IntegerField(),
    )
    delivery_data = serializers.DictField(
        child=serializers.DictField(),
    )


class CreateOrderResponseSerializer(serializers.Serializer):
    """
    Serializer for the response after creating an order.
    {
    "order_id": 123,
    "status": "PROCESSING",
    "message": "Заказ принят. Отправление передано в транспортные компании
    и ожидает окончательного подтверждения регистрации.
    Номер отслеживания появится после подтверждения."
}
    """
    order_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()



# Сериалайзеры для просмотра статусов заказов и отправлений, созданных во внещних системах, привязанных к заказу (Order)

class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        fields = (
            "unique_product",
            "product_name",
            "amount",
            "price",
        )


class CdekDeliveryStatusHistorySerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = CdekDeliveryStatusHistory
        fields = (
            "status_code",
            "status_name",
            "status_date",
            "city",
            "is_deleted",
        )


class CdekDeliveryStatusSerializer(serializers.ModelSerializer):
    status_history = CdekDeliveryStatusHistorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = CdekDelivery
        fields = (
            "tariff_code",
            "delivery_mode",
            "delivery_mode_name",
            "shipment_point",
            "delivery_point",
            "location_from",
            "location_from_region",
            "location_from_district",
            "location_to",
            "location_to_region",
            "location_to_district",
            "shipment_track_id",
            "shipment_price",
            "order_status",
            "stock_status",
            "cdek_uuid",
            "status_history",
        )


class OrderDeliveryStatusSerializer(serializers.ModelSerializer):
    products = OrderProductSerializer(
        source="items",
        many=True,
        read_only=True,
    )

    cdek = CdekDeliveryStatusSerializer(
        read_only=True,
    )

    class Meta:
        model = OrderDelivery
        fields = (
            "id",
            "shop",
            "delivery_type",
            "status",
            "created_at",
            "products",
            "cdek",
        )


class OrderStatusSerializer(serializers.ModelSerializer):
    deliveries = OrderDeliveryStatusSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "created_at",
            "status",
            "deliveries",
        )




class ReturnRequestCreateSerializer(serializers.ModelSerializer):
    """
       Сериализатор для создания покупателем заявки
       на возврат доставленного заказа.
       """

    class Meta:
        model = ReturnRequest
        fields = (
            "order_delivery",
            "reason",
        )

    order_delivery = serializers.PrimaryKeyRelatedField(
        queryset=OrderDelivery.objects.all(),
    )


class ReturnRequestSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения заявки покупателя
    на возврат заказа.
    """

    shop = serializers.ReadOnlyField(source="shop.name")
    seller = serializers.ReadOnlyField(source="seller.email")
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = ReturnRequest
        fields = (
            "id",
            "order_delivery",
            "owner",
            "shop",
            "seller",
            "status",
            "status_display",
            "reason",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "shop",
            "seller",
            "status",
            "status_display",
            "rejection_reason",
            "created_at",
            "updated_at",
        )