from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User, Role, UserRole, Session


@admin.register(User)
class UserAdmin(UserAdmin):
    ordering = ("email",)

    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "is_staff",
        "is_active",
        "is_superuser",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
        "middle_name",
        "phone_number",
    )

    fieldsets = (
        ("Auth", {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "middle_name",
                    "phone_number",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("date_joined",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
    )

    search_fields = (
        "name",
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_user_email",
        "role",
    )

    list_filter = (
        "role",
    )

    autocomplete_fields = (
        "user",
        "role",
    )

    search_fields = (
        "user__email",
        "role__name",
    )

    @admin.display(description="Email")
    def get_user_email(self, obj):
        return obj.user.email


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "expires_at",
        "is_active",
        "ip_address",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "user__email",
        "token",
        "ip_address",
    )

    autocomplete_fields = (
        "user",
    )

    ordering = (
        "-created_at",
    )