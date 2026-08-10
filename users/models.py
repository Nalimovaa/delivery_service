from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from users.managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    # common
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )

    is_active = models.BooleanField(
        "active",
        default=True,
        help_text=(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )

    # auth data
    date_joined = models.DateTimeField("date joined", default=timezone.now)
    email = models.EmailField(unique=True)

    # personal data
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    location_to = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Город получателя",
    )

    USERNAME_FIELD = 'email'
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name}"

    @property
    def fullname(self) -> str:
        parts = [self.first_name, self.last_name, self.middle_name]
        return " ".join(filter(None, parts))

    def soft_delete(self):
        """Soft removal of a user"""
        self.is_active = False
        self.save()


class Role(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_users")

    def __str__(self):
        return f"{self.user} → {self.role}"


class Session(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    token = models.CharField(max_length=512)  # JWT токен
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    user_agent = models.CharField(max_length=256, blank=True)  # user device
    ip_address = models.GenericIPAddressField(blank=True, null=True)  # User's IP address

    def __str__(self):
        return f"Session for {self.user}"

