from django.contrib import admin
from decimal import Decimal
from order.models import CartItem, Cart
from product.models import Product, UniqueProduct


class UniqueProductInline(admin.TabularInline):
    model = UniqueProduct
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "shop",
    )

    list_filter = (
        "shop",
    )

    search_fields = (
        "name",
        "shop__name",
    )

    autocomplete_fields = (
        "shop",
    )

    inlines = (UniqueProductInline,)


@admin.register(UniqueProduct)
class UniqueProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "ware_key",
        "price",
        "stock",
        "color",
        "size",
    )

    list_filter = (
        "product__shop",
        "color",
        "size",
    )

    search_fields = (
        "ware_key",
        "product__name",
    )

    autocomplete_fields = (
        "product",
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "items_count",
        "items_total",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "owner__email",
        "owner__first_name",
        "owner__last_name",
    )

    autocomplete_fields = (
        "owner",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "items_total",
    )

    ordering = (
        "-updated_at",
    )

    @admin.display(description="Количество позиций")
    def items_count(self, obj):
        return obj.items.count()

    @admin.display(description="Итого товаров")
    def items_total(self, obj):
        return sum(
            (
                item.amount * item.unique_product.price
                for item in obj.items.select_related(
                "unique_product"
            ).all()
            ),
            Decimal("0"),
        )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart",
        "unique_product",
        "product_name",
        "ware_key",
        "amount",
        "price",
    )

    search_fields = (
        "cart__owner__email",
        "unique_product__ware_key",
        "unique_product__product__name",
        "unique_product__color",
        "unique_product__size",
    )

    autocomplete_fields = (
        "cart",
        "unique_product",
    )

    readonly_fields = (
        "price",
    )

    ordering = (
        "cart",
        "id",
    )

    @admin.display(description="Товар")
    def product_name(self, obj):
        return obj.unique_product.product.name

    @admin.display(description="Артикул")
    def ware_key(self, obj):
        return obj.unique_product.ware_key

    @admin.display(description="Цена")
    def price(self, obj):
        return obj.unique_product.price