from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from core.models import AccessRolesRules, BusinessElement
from django.contrib.auth import get_user_model

User = get_user_model()


# Matching HTTP methods with permissions
METHOD_TO_PERMISSION = {
    "GET": ("read_permission", "read_all_permission"),
    "POST": ("create_permission", None),
    "PUT": ("update_permission", "update_all_permission"),
    "PATCH": ("update_permission", "update_all_permission"),
    "DELETE": ("delete_permission", "delete_all_permission"),
}

AUTH_REQUIRED_METHODS = ("POST", "PUT", "PATCH", "DELETE")



class IsCustomAuthenticated(BasePermission):
    """Only verification that the user is authorized via JWT."""

    def has_permission(self, request, view):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise NotAuthenticated("Authorization header missing or invalid")

        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated("User not authenticated")

        return True



class RolePermission(BasePermission):
    """
    RBAC permission:
    - View-level permission check (before obtaining the object)
    - Specific object-level permission check
    """

    def has_permission(self, request, view):
        # If the user is a superuser, we grant full access without further verification.
        if getattr(request.user, "is_superuser", False):
            return True

        # If the user is not authorized, we only allow access if allow_guest = True is explicitly specified in View.
        if not request.user or not request.user.is_authenticated:
            return getattr(view, "allow_guest", False)

        # Trying to get the name of a business element that can be explicitly specified in ViewSet.
        element_name = getattr(view, "business_element", None)

        # Unless explicitly specified, we attempt to identify the element through the queryset model.
        if not element_name and hasattr(view, "queryset") and view.queryset:
            element_name = view.queryset.model.__name__

        if not element_name:
            raise PermissionDenied("Business element not defined")

        # Search for the corresponding BusinessElement in the database
        element = BusinessElement.objects.filter(name=element_name).first()

        # If such a business element is not registered, we prohibit access.
        if not element:
            raise PermissionDenied(f"No BusinessElement defined for {element_name}")

        # We determine which permission fields to check.
        perm, perm_all = METHOD_TO_PERMISSION.get(request.method, (None, None))

        # If the method is not supported in the RBAC system, we prohibit it.
        if not perm:
            raise PermissionDenied("Method not allowed")

        # Get all roles of the current user
        user_roles = request.user.user_roles.select_related("role")

        # Receive all access rules
        rules = AccessRolesRules.objects.filter(
            role__in=[ur.role for ur in user_roles],
            element=element
        )

        # Проверяем, есть ли у пользователя необходимое право
        if any(
                getattr(rule, perm, False) or
                (perm_all and getattr(rule, perm_all, False))
                for rule in rules
        ):
            return True

        raise PermissionDenied(f"No {perm} permission")

    def has_object_permission(self, request, view, obj):

        # Superuser has full access
        if getattr(request.user, "is_superuser", False):
            return True

        # We determine the name of the business element: either from View or through the object model class
        element_name = getattr(view, "business_element", obj.__class__.__name__)

        # Get BusinessElement from the database
        element = BusinessElement.objects.filter(name=element_name).first()

        # If the element is not registered, we prohibit it
        if not element:
            raise PermissionDenied(f"No BusinessElement defined for {element_name}")

        # We determine which permissions to check
        perm, perm_all = METHOD_TO_PERMISSION.get(request.method, (None, None))

        # If the method is not supported, we prohibit it
        if not perm:
            raise PermissionDenied("Method not allowed")

        # Identify the owner of the property
        owner = (
                getattr(obj, "owner", None)
                or getattr(obj, "user", None)
                or getattr(getattr(obj, "shop", None), "owner", None)
                or getattr(
            getattr(getattr(obj, "product", None), "shop", None),
            "owner",
            None,
        )
                or (obj if isinstance(obj, User) else None)
        )

        # Check whether the current user is the owner
        is_owner = owner == request.user

        # Get user roles
        user_roles = request.user.user_roles.select_related("role")

        # Obtain access rules for user roles
        rules = AccessRolesRules.objects.filter(
            role__in=[ur.role for ur in user_roles],
            element=element
        )

        # We check every rule
        for rule in rules:

            # If there is a permission of the type *_all_permission, we grant full access to the object.
            if perm_all and getattr(rule, perm_all, False):
                return True

            # If there is a normal permission and the user is the owner of the object, we allow access.
            if getattr(rule, perm, False) and is_owner:
                return True

        # If none of the rules apply, we deny access.
        raise PermissionDenied("You do not have permission for this object")
