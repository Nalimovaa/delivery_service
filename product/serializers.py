from rest_framework import serializers
from decimal import Decimal
from order.models import CartItem, Cart
from product.models import Product, UniqueProduct


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


class CartItemSerializer(serializers.ModelSerializer):
    """Строка корзины (конкретный товар в корзине, с указанием количества)"""
    price = serializers.DecimalField(
        source="unique_product.price",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = (
            "id",
            "unique_product",
            "amount",
            "price",
        )
        read_only_fields = (
            "id",
        )

    def validate_amount(self, amount):
        if amount <= 0:
            raise serializers.ValidationError(
                "Количество должно быть больше нуля."
            )

        return amount

    def validate_unique_product(self, unique_product):
        if not UniqueProduct.objects.filter(
            id=unique_product.id
        ).exists():
            raise serializers.ValidationError(
                "Товар не найден."
            )

        return unique_product


class CartSerializer(serializers.ModelSerializer):
    """Корзина пользователя (пользователь добавил товары в корзину, но еще не оформил заказ)"""
    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    items_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "owner",
            "created_at",
            "updated_at",
            "items",
            "items_total",
        )
        read_only_fields = (
            "id",
            "owner",
            "created_at",
            "updated_at",
            "items",
            "items_total",
        )

    def get_items_total(self, obj):
        return sum(
            (
                item.amount * item.unique_product.price
                for item in obj.items.all()
            ),
            Decimal("0"),
        )


class AddCartItemSerializer(serializers.Serializer):
    """Добавление товара в корзину (конкретный вариант товара с указанием количества)"""
    unique_product = serializers.PrimaryKeyRelatedField(
        queryset=UniqueProduct.objects.all()
    )
    amount = serializers.IntegerField(
        min_value=1,
        help_text="Количество добавляемых единиц товара",
    )

class UpdateCartItemSerializer(serializers.Serializer):
    """Обновление количества товара в корзине (конкретный вариант товара с указанием нового количества)"""
    amount = serializers.IntegerField(
        min_value=1,
        help_text="Новое количество товара в корзине.",
    )