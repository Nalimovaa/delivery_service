"""docker exec -it delivery_service-web-1 python manage.py test users.tests.test_permissions"""

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from core.models import (
    AccessRolesRules,
    BusinessElement,
)

from users.models import (
    Role,
    User,
    UserRole,
)

from users.permissions import (
    IsCustomAuthenticated,
    RolePermission,
)


class DummyView:
    business_element = "ShopDeliverySetting"


class TestRolePermission(TestCase):
    """ Тестирование системы ролевой авторизации (RBAC).

        Проверяется корректность работы класса RolePermission:
        - предоставление доступа пользователю с ролью Seller при наличии соответствующего разрешения;
        - проверка доступа к операциям чтения и создания объектов;
        - запрет выполнения операций при отсутствии необходимых прав;
        - предоставление полного доступа пользователю с правами суперпользователя.

        Дополнительно проверяется взаимодействие компонентов RBAC:
        - UserRole — связь пользователя с ролью;
        - BusinessElement — определение защищаемого бизнес-объекта;
        - AccessRolesRules — хранение правил доступа для ролей. """

    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.role = Role.objects.create(
            name="Seller",
        )

        UserRole.objects.create(
            user=self.user,
            role=self.role,
        )

        self.element = BusinessElement.objects.create(
            name="ShopDeliverySetting",
        )

        AccessRolesRules.objects.create(
            role=self.role,
            element=self.element,
            read_permission=True,
            create_permission=True,
            delete_permission=True,
        )

    def test_get_permission(self):
        request = self.factory.get("/")
        request.user = self.user

        permission = RolePermission()

        self.assertTrue(
            permission.has_permission(
                request,
                DummyView(),
            )
        )

    def test_post_permission(self):
        request = self.factory.post("/")
        request.user = self.user

        permission = RolePermission()

        self.assertTrue(
            permission.has_permission(
                request,
                DummyView(),
            )
        )

    def test_put_without_permission(self):
        request = self.factory.put("/")
        request.user = self.user

        permission = RolePermission()

        with self.assertRaises(Exception):
            permission.has_permission(
                request,
                DummyView(),
            )

    def test_superuser(self):
        self.user.is_superuser = True

        request = self.factory.delete("/")
        request.user = self.user

        permission = RolePermission()

        self.assertTrue(
            permission.has_permission(
                request,
                DummyView(),
            )
        )