"""docker exec -it delivery_service-web-1 python manage.py test users.tests.test_serializers"""

from django.test import TestCase

from users.models import Role, UserRole
from users.serializers import UserSerializer


class TestUserSerializer(TestCase):
    """ Тестирование сериализатора пользователя UserSerializer.

        Проверяется корректность работы сериализатора при создании нового пользователя:
        - успешная валидация данных пользователя;
        - корректное создание пользователя через serializer.save();
        - сохранение пароля в хешированном виде;
        - автоматическое назначение роли User после регистрации.

        Дополнительно проверяется обработка ошибок валидации:
        - отклонение данных при несовпадении основного пароля и подтверждения пароля.

        Тесты подтверждают корректную работу логики регистрации пользователя,
        реализованной в методе create() сериализатора. """

    def setUp(self):
        Role.objects.create(
            name="User",
        )

    def test_create_user(self):
        serializer = UserSerializer(
            data={
                "email": "user@test.com",
                "first_name": "User",
                "last_name": "Test",
                "middle_name": "Middle",
                "password": "12345678",
                "password_repeat": "12345678",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

        user = serializer.save()

        self.assertTrue(
            user.check_password("12345678")
        )

        self.assertTrue(
            UserRole.objects.filter(
                user=user,
            ).exists()
        )

    def test_password_mismatch(self):
        serializer = UserSerializer(
            data={
                "email": "user@test.com",
                "first_name": "User",
                "last_name": "Test",
                "middle_name": "Middle",
                "password": "123",
                "password_repeat": "456",
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )