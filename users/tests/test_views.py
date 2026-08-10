"""docker exec -it delivery_service-web-1 python manage.py test users.tests.test_views"""

import jwt

from django.conf import settings
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User, Session, Role, UserRole
from core.models import BusinessElement, AccessRolesRules


class TestUserViewSet(APITestCase):
    """ Тестирование UserViewSet.

        Проверяется работа основных пользовательских операций:

        - регистрация нового пользователя через публичный endpoint register;
        - авторизация пользователя через login с созданием JWT токена;
        - создание активной Session после успешного входа;
        - обработка ошибки при неверных учетных данных;
        - выход пользователя через logout с деактивацией JWT-сессии;
        - мягкое удаление пользователя (soft delete) с отключением активных сессий;
        - обновление профиля текущего пользователя;
        - ограничение доступа пользователя только собственными данными.

        Тесты подтверждают корректную работу пользовательского API,
        JWT-аутентификации и механизмов управления жизненным циклом аккаунта. """

    def setUp(self):
        self.role = Role.objects.create(
            name="User",
        )

        self.element = BusinessElement.objects.create(
            name="User",
        )

        AccessRolesRules.objects.create(
            role=self.role,
            element=self.element,
            read_permission=True,
            update_permission=True,
        )

        self.user = User.objects.create_user(
            email="user@test.com",
            password="12345678",
            first_name="User",
            last_name="Test",
            middle_name="Middle",
            phone_number="+1234567890",
            location_to="Test City",
        )

        UserRole.objects.create(
            user=self.user,
            role=self.role,
        )

        self.token = jwt.encode(
            {
                "user_id": self.user.id,
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        self.session = Session.objects.create(
            user=self.user,
            token=self.token,
            is_active=True,
        )


    def auth_header(self):
        return {
            "HTTP_AUTHORIZATION": f"Bearer {self.token}"
        }


    def test_register_success(self):
        response = self.client.post(
            "/api/users/register/",
            {
                "email": "new@test.com",
                "first_name": "New",
                "last_name": "User",
                "middle_name": "Middle",
                "phone_number": "+1234567890",
                "location_to": "Test City",
                "password": "12345678",
                "password_repeat": "12345678",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["email"],
            "new@test.com",
        )

        self.assertTrue(
            User.objects.filter(
                email="new@test.com"
            ).exists()
        )


    def test_login_success(self):
        response = self.client.post(
            "/api/users/login/",
            {
                "email": "user@test.com",
                "password": "12345678",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "token",
            response.data,
        )

        self.assertTrue(
            Session.objects.filter(
                user=self.user,
                is_active=True,
            ).exists()
        )


    def test_login_invalid_password(self):
        response = self.client.post(
            "/api/users/login/",
            {
                "email": "user@test.com",
                "password": "wrong_password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


    def test_logout_success(self):

        response = self.client.post(
            "/api/users/logout/",
            **self.auth_header(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.session.refresh_from_db()

        self.assertFalse(
            self.session.is_active,
        )


    def test_soft_delete_user(self):

        response = self.client.post(
            "/api/users/delete/",
            **self.auth_header(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_active,
        )

        self.session.refresh_from_db()

        self.assertFalse(
            self.session.is_active,
        )


    def test_update_profile_success(self):

        response = self.client.patch(
            "/api/users/update_profile/",
            {
                "first_name": "Updated",
            },
            format="json",
            **self.auth_header(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.first_name,
            "Updated",
        )

    def test_user_can_get_own_profile(self):
        response = self.client.get(
            f"/api/users/{self.user.id}/",
            **self.auth_header(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["email"],
            self.user.email,
        )

    def test_user_cannot_access_another_user(self):
        another_user = User.objects.create_user(
            email="another@test.com",
            password="12345678",
            first_name="Another",
            last_name="User",
            middle_name="Middle",
            phone_number="+1234567890",
        location_to="Test City",
        )

        response = self.client.get(
            f"/api/users/{another_user.id}/",
            **self.auth_header(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )