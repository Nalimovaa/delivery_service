
from rest_framework import serializers
from product.models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "shop",
        )

    def validate_shop(self, shop):
        request = self.context.get("request")

        if request and shop.owner != request.user:
            raise serializers.ValidationError(
                "Вы можете создавать товары только в своих магазинах."
            )

        return shop
