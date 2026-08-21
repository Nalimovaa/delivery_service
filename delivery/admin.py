from django.contrib import admin

from delivery.models import (
    OrderDelivery,
    CdekDelivery,
    CDEKTariff, CDEKCity, CDEKDeliveryPoint,
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


@admin.register(CDEKCity)
class CDEKCityAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "city",
        "region",
        "country_code",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "country_code",
        "region",
    )

    search_fields = (
        "code",
        "city",
        "region",
        "city_uuid",
        "fias_guid",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "country_code",
        "region",
        "city",
    )


@admin.register(CDEKDeliveryPoint)
class CDEKDeliveryPointAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "city",
        "region",
        "type",
        "status",
        "is_handout",
        "is_reception",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "status",
        "type",
        "is_handout",
        "is_reception",
        "country_code",
        "region",
    )

    search_fields = (
        "code",
        "name",
        "city",
        "region",
        "address",
        "address_full",
        "uuid",
        "city_uuid",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "country_code",
        "region",
        "city",
        "name",
    )