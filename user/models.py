from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """Менеджер користувачів для BaseUser"""

    def create_user(self, email, password=None, **extra_fields):
        """Створення звичайного користувача"""
        if not email:
            raise ValueError(_("Email обов'язковий"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Створення суперюзера"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Specialty(models.Model):
    """Спеціальність викладача"""
    name = models.CharField(_("Назва спеціальності"), max_length=100, unique=True)

    def __str__(self):
        return self.name


class BaseUser(AbstractBaseUser, PermissionsMixin):
    """Базовий користувач"""

    class UserType(models.TextChoices):
        STUDENT = "student", _("Студент")
        TEACHER = "teacher", _("Викладач")

    email = models.EmailField(_("Email"), unique=True)
    first_name = models.CharField(_("Ім'я"), max_length=50)
    last_name = models.CharField(_("Прізвище"), max_length=50)
    is_active = models.BooleanField(_("Активний"), default=True)
    is_staff = models.BooleanField(_("Персонал"), default=False)

    user_type = models.CharField(
        _("Тип користувача"),
        max_length=10,
        choices=UserType.choices,
        default=UserType.STUDENT,
    )

    age = models.PositiveIntegerField(_("Вік"), null=True, blank=True)
    bio = models.TextField(_("Біографія"), blank=True)
    rating = models.FloatField(_("Рейтинг"), default=0)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_user_type_display()})"


class Teacher(models.Model):
    """Профіль викладача"""
    user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="teacher_profile"
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.SET_NULL,
        null=True,
        related_name="teachers",
        verbose_name=_("Спеціальність")
    )

    def __str__(self):
        return f"Викладач: {self.user.first_name} {self.user.last_name} ({self.specialty})"


class Student(models.Model):
    """Профіль студента"""
    user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    def __str__(self):
        return f"Студент: {self.user.first_name} {self.user.last_name}"
