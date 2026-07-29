"""docker exec -it delivery_service-web-1 python manage.py test users.tests.test_managers"""

from django.test import TestCase

from users.models import User, Role, UserRole


class TestCustomUserManager(TestCase):
    """ Тестирование пользовательского менеджера CustomUserManager.

        Проверяется корректность создания обычных пользователей и суперпользователей:
        - создание пользователя с валидным email и паролем;
        - корректное хеширование пароля при создании пользователя;
        - обработка ошибки при попытке создания пользователя без email;
        - создание суперпользователя с правами администратора;
        - автоматическое назначение роли Admin при создании суперпользователя. """

    def setUp(self):
        self.admin_role = Role.objects.create(
            name="Admin",
        )

    def test_create_user(self):
        user = User.objects.create_user(
            email="user@test.com",
            password="12345678",
        )

        self.assertEqual(
            user.email,
            "user@test.com",
        )

        self.assertTrue(
            user.check_password("12345678"),
        )

    def test_create_user_without_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="",
                password="12345678",
            )

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@test.com",
            password="12345678",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

        self.assertTrue(
            UserRole.objects.filter(
                user=user,
                role=self.admin_role,
            ).exists()
        )