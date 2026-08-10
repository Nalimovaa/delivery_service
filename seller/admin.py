from django.contrib import admin

from seller.models import Shop, ShopDeliverySetting


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner",
        "location_from",
        "carrier",
    )

    search_fields = (
        "name",
        "owner__email",
        "owner__first_name",
        "owner__last_name",
        "location_from",
        "carrier",
    )

    autocomplete_fields = (
        "owner",
    )

    ordering = (
        "name",
    )


@admin.register(ShopDeliverySetting)
class ShopDeliverySettingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "shop",
        "tariff_code",
        "tariff_name",
        "delivery_mode",
        "created_at",
    )

    @admin.display(description="Код тарифа")
    def tariff_code(self, obj):
        return obj.tariff.tariff_code

    @admin.display(description="Название")
    def tariff_name(self, obj):
        return obj.tariff.tariff_name

    @admin.display(description="Режим доставки")
    def delivery_mode(self, obj):
        return obj.tariff.delivery_mode_name

    search_fields = (
        "shop__name",
        "shop__owner__email",
        "tariff__tariff_name",
        "tariff__tariff_code",
    )

    list_filter = (
        "created_at",
    )

    autocomplete_fields = (
        "shop",
        "tariff",
    )

    ordering = (
        "-created_at",
    )