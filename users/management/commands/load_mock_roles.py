# python manage.py load_mock_roles

from django.core.management.base import BaseCommand
from core.models import BusinessElement, AccessRolesRules
from users.models import Role



class Command(BaseCommand):
    help = "Load mock roles, business elements and access rules into the database"

    def handle(self, *args, **kwargs):
        # 1. Creating roles
        roles_data = [
            ("Admin", "Full access to the system"),
            ("Seller", "Access to own store, products, orders and delivery settings"),
            ("User", "Access own orders, edit own details, browse stores and products"),
            ("Guest", "Viewing public information only"),
        ]

        roles = {}
        for name, description in roles_data:
            role, _ = Role.objects.get_or_create(name=name, defaults={"description": description})
            roles[name] = role

        self.stdout.write(self.style.SUCCESS("Roles loaded."))

        # 2. Creating business elements
        elements_data = [
            "User",
            "Product",
            "UniqueProduct",
            "Shop",
            "ShopDeliverySetting",
            "SellerRequest",
            "Order",
            "Cart",
            "Role",
            "UserRole",
            "BusinessElement",
            "AccessRolesRules"]

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
            {
                "role": "Admin",
                "element": "UniqueProduct",
                "read_all_permission": True,
                "update_all_permission": True,
                "create_permission": True,
                "delete_all_permission": True,
            },
            # Admin — заявки на получение Seller
            {
                "role": "Admin",
                "element": "SellerRequest",
                "read_all_permission": True,
                "update_all_permission": True,
                "create_permission": True,
                "delete_all_permission": True,
            },
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

            # Seller — Access to own stores, to create and edit products related to the seller's store and view,
            # edit user orders related to that store and access only to own shop delivery settings
            {"role": "Seller", "element": "Shop",
             "update_permission": True, "create_permission": True, "read_permission": True},
            {"role": "Seller",
             "element": "Product",
             "update_permission": True,
             "create_permission": True,
             "read_permission": True,
             "delete_permission": True,
             },
            {
                "role": "Seller",
                "element": "UniqueProduct",
                "update_permission": True,
                "create_permission": True,
                "read_permission": True,
                "delete_permission": True,
            },
            {"role": "Seller", "element": "Order", "read_permission": True, "update_permission": True},
            {"role": "Seller", "element": "ShopDeliverySetting",
             "read_permission": True, "create_permission": True, "delete_permission": True},

            # User — Access own orders, edit own details, browse stores and products
            {"role": "User", "element": "Order", "read_permission": True, "create_permission": True,
             "update_permission": True, "delete_permission": True},
            {
                "role": "User",
                "element": "Cart",
                "read_permission": True,
                "create_permission": True,
                "update_permission": True,
                "delete_permission": True,
            },
            {"role": "User", "element": "User", "read_permission": True, "update_permission": True},
            {"role": "User", "element": "Shop", "read_all_permission": True},
            {"role": "User", "element": "Product", "read_all_permission": True},
            {
                "role": "User",
                "element": "UniqueProduct",
                "read_all_permission": True,
            },

            # Guest — Viewing public information only
            {"role": "Guest", "element": "Product", "read_all_permission": True},
            {
                "role": "Guest",
                "element": "UniqueProduct",
                "read_all_permission": True,
            },
            # User — может создать заявку и видеть свои заявки
            {
                "role": "User",
                "element": "SellerRequest",
                "read_permission": True,
                "create_permission": True,
            },
            {"role": "Guest", "element": "Shop", "read_all_permission": True},
        ]

        for rule_data in rules_data:
            role = roles[rule_data.pop("role")]
            element = elements[rule_data.pop("element")]
            AccessRolesRules.objects.update_or_create(role=role, element=element, defaults=rule_data)

        self.stdout.write(self.style.SUCCESS("Access rules loaded successfully."))

