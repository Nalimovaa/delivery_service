from django.contrib import admin

from delivery.models import (
    OrderDelivery,
    CdekDelivery,
    CDEKTariff, CDEKCity, CDEKDeliveryPoint, CdekRequestLog, CdekDeliveryStatusHistory, CdekReturn,
)


@admin.register(OrderDelivery)
class OrderDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "shop",
        "delivery_type",
        "status",
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
        "cdek_uuid",
        "shipment_track_id",
        "order_status",
        "preliminary_price",
        "shipment_price",
        "stock_status",
    )

    list_filter = (
        "order_status",
    )

    search_fields = (
        "cdek_uuid",
        "shipment_track_id",
        "order_delivery__id",
        "order_delivery__order__id",
        "stock_status",
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

@admin.register(CdekDeliveryStatusHistory)
class CdekDeliveryStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "cdek_delivery",
        "cdek_uuid",
        "status_code",
        "status_name",
        "status_date",
        "city",
        "is_deleted",
        "created_at",
    )

    list_filter = (
        "status_code",
        "is_deleted",
        "status_date",
        "created_at",
    )

    search_fields = (
        "status_code",
        "status_name",
        "city",
        "cdek_delivery__cdek_uuid",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-status_date",
    )

    @admin.display(
        description="CDEK UUID",
        ordering="cdek_delivery__cdek_uuid",
    )
    def cdek_uuid(self, obj):
        return obj.cdek_delivery.cdek_uuid


@admin.register(CdekRequestLog)
class CdekRequestLogAdmin(admin.ModelAdmin):
    list_display = (
        "cdek_delivery",
        "cdek_uuid",
        "request_type",
        "state",
        "date_time",
        "error_code",
        "created_at",
    )

    list_filter = (
        "request_type",
        "state",
        "error_code",
        "date_time",
        "created_at",
    )

    search_fields = (
        "cdek_uuid",
        "request_type",
        "state",
        "error_code",
        "error_message",
        "cdek_delivery__cdek_uuid",
    )

    readonly_fields = (
        "created_at",
        "cdek_uuid",
        "response_data",
    )

    ordering = (
        "-created_at",
    )


@admin.register(CdekReturn)
class CdekReturnAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "return_request",
        "cdek_delivery",
        "cdek_uuid",
        "tariff_code",
        "request_state",
        "cdek_status_code",
        "cdek_status_name",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "request_state",
        "cdek_status_code",
        "created_at",
    )

    search_fields = (
        "cdek_uuid",
        "cdek_status_code",
        "cdek_status_name",
        "return_request__id",
        "return_request__owner__email",
        "cdek_delivery__id",
        "cdek_delivery__cdek_uuid",
    )

    autocomplete_fields = (
        "return_request",
        "cdek_delivery",
    )

    ordering = ("-created_at",)