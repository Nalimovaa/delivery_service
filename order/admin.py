from django.contrib import admin

from order.models import Order, OrderProduct


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0
    autocomplete_fields = ("unique_product", "order_delivery")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "id",
        "owner__email",
        "owner__first_name",
        "owner__last_name",
    )

    autocomplete_fields = (
        "owner",
    )

    ordering = ("-created_at",)

    inlines = (OrderProductInline,)


@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product_name",
        "amount",
        "price",
        "order_delivery",
    )

    search_fields = (
        "product_name",
        "unique_product__ware_key",
        "order__id",
    )

    autocomplete_fields = (
        "order",
        "order_delivery",
        "unique_product",
    )