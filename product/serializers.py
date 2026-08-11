from rest_framework import serializers
from product.models import Product, UniqueProduct
from seller.models import Shop

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "shop",
        )
        read_only_fields = (
            "id",
        )

    def validate_shop(self, shop):
        request = self.context.get("request")

        if (
                not request
                or not request.user
                or not request.user.is_authenticated
        ):
            raise serializers.ValidationError(
                "Пользователь не авторизован."
            )

        if shop.owner != request.user:
            raise serializers.ValidationError(
                "Вы можете создавать товары только в своих магазинах."
            )

        return shop


class UniqueProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniqueProduct
        fields = (
            "id",
            "product",
            "ware_key",
            "price",
            "color",
            "size",
            "height",
            "length",
            "width",
            "weight",
            "stock",
        )
        read_only_fields = (
            "id",
            "stock",
        )

    def validate_product(self, product):
        request = self.context.get("request")

        if (
                not request
                or not request.user
                or not request.user.is_authenticated
        ):
            raise serializers.ValidationError(
                "Пользователь не авторизован."
            )

        if product.shop.owner != request.user:
            raise serializers.ValidationError(
                "Вы можете добавлять варианты только в свои товары."
            )

        return product


class StockAmountSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        min_value=1,
        help_text="Количество товара.",
    )