from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import Role, UserRole


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    # Additional field for password confirmation
    password_repeat = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "middle_name",
            "phone_number",
            "location_to",
            "password",
            "password_repeat",
        )
        extra_kwargs = {
            "password": {"write_only": True},  # We do not return the password in the response.
        }

    def validate(self, attrs):
        # Checking password matches
        if attrs.get("password") != attrs.get("password_repeat"):
            raise serializers.ValidationError({"password_repeat": "Passwords do not match"})

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_repeat")
        raw_password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(raw_password)
        user.save()

        default_role, _ = Role.objects.get_or_create(name="User")
        UserRole.objects.create(user=user, role=default_role)

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise serializers.ValidationError({"detail": "Email and password required"})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User is deactivated"})

        if not user.check_password(password):
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        data["user"] = user
        return data


