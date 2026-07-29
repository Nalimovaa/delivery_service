"""docker exec -it delivery_service-web-1 python manage.py test users.tests.test_is_authenticated"""

from django.test import TestCase
from rest_framework.exceptions import NotAuthenticated
from rest_framework.test import APIRequestFactory

from users.models import User
from users.permissions import IsCustomAuthenticated


class TestIsCustomAuthenticated(TestCase):
    """ Тестирование проверки аутентификации пользователя.

        Проверяется корректность работы класса IsCustomAuthenticated:
        - предоставление доступа авторизованному пользователю с корректным JWT-заголовком Authorization;
        - отклонение запросов без заголовка Authorization;
        - запрет доступа для неаутентифицированного пользователя.

        Тесты подтверждают, что перед выполнением проверки ролевых прав пользователь
        должен пройти обязательный этап аутентификации. """

    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = User.objects.create(
            email="user@test.com",
        )

    def test_success(self):
        request = self.factory.get(
            "/",
            HTTP_AUTHORIZATION="Bearer token",
        )

        request.user = self.user

        permission = IsCustomAuthenticated()

        self.assertTrue(
            permission.has_permission(
                request,
                None,
            )
        )

    def test_without_header(self):
        request = self.factory.get("/")
        request.user = self.user

        permission = IsCustomAuthenticated()

        with self.assertRaises(NotAuthenticated):
            permission.has_permission(
                request,
                None,
            )

    def test_anonymous(self):
        request = self.factory.get(
            "/",
            HTTP_AUTHORIZATION="Bearer token",
        )

        request.user = None

        permission = IsCustomAuthenticated()

        with self.assertRaises(NotAuthenticated):
            permission.has_permission(
                request,
                None,
            )