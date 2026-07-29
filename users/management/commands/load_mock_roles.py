from django.core.management.base import BaseCommand
from core.models import BusinessElement, AccessRolesRules
from users.models import Role



class Command(BaseCommand):
    help = "Load mock roles, business elements and access rules into the database"

    def handle(self, *args, **kwargs):
        # 1. Creating roles
        roles_data = [
            ("Admin", "Full access to the system"),
            ("Manager", "Access to create and edit products related to the seller's store "
                        "and view and edit user orders related to that store"),
            ("Seller", "Access only to own stores"),
            ("User", "Access own orders, edit own details, browse stores and products"),
            ("Guest", "Viewing public information only"),
        ]

        roles = {}
        for name, description in roles_data:
            role, _ = Role.objects.get_or_create(name=name, defaults={"description": description})
            roles[name] = role

        self.stdout.write(self.style.SUCCESS("Roles loaded."))

        # 2. Creating business elements
        elements_data = ["User", "Product", "Shop", "ShopDeliverySetting", "Order", "Role", "UserRole", "BusinessElement", "AccessRolesRules"]
        elements = {}
        for name in elements_data:
            element, _ = BusinessElement.objects.get_or_create(name=name)
            elements[name] = element

        self.stdout.write(self.style.SUCCESS("Business elements loaded."))

        # 3. Creating access rules
        rules_data = [
            # Admin — Full access to the system
            {"role": "Admin", "element": "User", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},
            {"role": "Admin", "element": "Product", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},
            {"role": "Admin", "element": "Shop", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},
            {"role": "Admin", "element": "Order", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},
            {"role": "Admin", "element": "BusinessElement", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},
            {"role": "Admin", "element": "AccessRolesRules", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},
            {"role": "Admin", "element": "Role", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},
            {"role": "Admin", "element": "UserRole", "read_all_permission": True, "update_all_permission": True,
             "create_permission": True, "delete_all_permission": True},

            # Manager — Access to create and edit products related to the seller's store and view
            # and edit user orders related to that store
            {"role": "Manager", "element": "Product", "update_permission": True, "create_permission": True},
            {"role": "Manager", "element": "Order", "read_permission": True,
             "update_permission": True, "read_all_permission": True},

            # Seller — Access only to own stores
            {"role": "Seller", "element": "Shop",
             "update_permission": True, "create_permission": True, "read_permission": True},

            # Seller - Access only to own shop delivery settings
            {"role": "Seller", "element": "ShopDeliverySetting",
             "read_permission": True, "create_permission": True, "delete_permission": True},

            # User — Access own orders, edit own details, browse stores and products
            {"role": "User", "element": "Order", "read_permission": True, "create_permission": True,
             "update_permission": True, "delete_permission": True},
            {"role": "User", "element": "User", "read_permission": True, "update_permission": True},
            {"role": "User", "element": "Shop", "read_all_permission": True},
            {"role": "User", "element": "Product", "read_all_permission": True},

            # Guest — Viewing public information only
            {"role": "Guest", "element": "Product", "read_all_permission": True},
            {"role": "Guest", "element": "Shop", "read_all_permission": True},
        ]

        for rule_data in rules_data:
            role = roles[rule_data.pop("role")]
            element = elements[rule_data.pop("element")]
            AccessRolesRules.objects.update_or_create(role=role, element=element, defaults=rule_data)

        self.stdout.write(self.style.SUCCESS("Access rules loaded successfully."))

