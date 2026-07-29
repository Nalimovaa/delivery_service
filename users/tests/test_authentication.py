"""docker exec -it delivery_service-web-1 python manage.py test users.tests.test_authentication"""

import jwt

from django.conf import settings
from django.test import TestCase

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from users.authentication import JWTTokenAuthentication
from users.models import Session, User


class TestJWTAuthentication(TestCase):
    """ Тестирование JWT-аутентификации пользователя.

        Проверяется корректность работы класса JWTTokenAuthentication:
        - успешная аутентификация пользователя по валидному JWT-токену;
        - отклонение некорректного JWT-токена;
        - запрет аутентификации при неактивной пользовательской сессии;
        - обработка запросов без заголовка Authorization. """

    def setUp(self):
        self.user = User.objects.create(
            email="user@test.com",
        )

        self.token = jwt.encode(
            {"user_id": self.user.id},
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        Session.objects.create(
            user=self.user,
            token=self.token,
            is_active=True,
        )

        self.auth = JWTTokenAuthentication()
        self.factory = APIRequestFactory()

    def test_authenticate_success(self):
        request = self.factory.get(
            "/",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        user, token = self.auth.authenticate(request)

        self.assertEqual(user, self.user)
        self.assertEqual(token, self.token)

    def test_invalid_token(self):
        request = self.factory.get(
            "/",
            HTTP_AUTHORIZATION="Bearer invalid",
        )

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_inactive_session(self):
        Session.objects.update(
            is_active=False,
        )

        request = self.factory.get(
            "/",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_without_authorization_header(self):
        request = self.factory.get("/")

        self.assertIsNone(
            self.auth.authenticate(request)
        )