from django.contrib import admin

from seller.models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner",
    )

    search_fields = (
        "name",
        "owner__email",
        "owner__first_name",
        "owner__last_name",
    )

    autocomplete_fields = (
        "owner",
    )

    ordering = (
        "name",
    )