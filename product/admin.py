from django.contrib import admin

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