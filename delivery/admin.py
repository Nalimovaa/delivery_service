from django.contrib import admin

from delivery.models import (
    OrderDelivery,
    CdekDelivery,
    CDEKTariff,
)


@admin.register(OrderDelivery)
class OrderDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "shop",
        "delivery_type",
        "created_at",
    )

    list_filter = (
        "delivery_type",
        "created_at",
    )

    search_fields = (
        "id",
        "order__id",
        "shop__name",
    )

    autocomplete_fields = (
        "order",
        "shop",
    )

    ordering = ("-created_at",)


@admin.register(CdekDelivery)
class CdekDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_delivery",
        "tariff_code",
        "shipment_track_id",
        "order_status",
        "preliminary_price",
        "shipment_price",
    )

    list_filter = (
        "order_status",
    )

    search_fields = (
        "cdek_uuid",
        "shipment_track_id",
        "order_delivery__id",
        "order_delivery__order__id",
    )

    autocomplete_fields = (
        "order_delivery",
    )


@admin.register(CDEKTariff)
class CDEKTariffAdmin(admin.ModelAdmin):
    list_display = (
        "tariff_code",
        "tariff_name",
        "delivery_mode_name",
        "weight_min",
        "weight_max",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "delivery_mode_name",
        "is_active",
    )

    search_fields = (
        "tariff_name",
        "tariff_code",
    )

    ordering = (
        "tariff_name",
        "tariff_code",
    )