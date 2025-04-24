from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    name = models.CharField(_("Country"), max_length=100, unique=True)

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(_("City"), max_length=100)
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="cities",
        verbose_name=_("Country"),
    )

    class Meta:
        unique_together = ("name", "country")
        verbose_name_plural = "Cities"

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class Subject(models.Model):
    name = models.CharField(_("Subject"), max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(_("Language"), max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CategoriesOfStudents(models.Model):
    CATEGORY_CHOICES = [
        ("1-4", _("Grades 1‑4")),
        ("5-8", _("Grades 5‑8")),
        ("9-12", _("Grades 9‑12")),
        ("adult", _("Adult")),
    ]
    name = models.CharField(max_length=10, choices=CATEGORY_CHOICES, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_name_display()


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class BaseUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("Email"), unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"

    ROLES_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_TEACHER, "Teacher"),
    ]
    role = models.CharField(max_length=10, choices=ROLES_CHOICES, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Teacher(models.Model):
    user = models.OneToOneField(
        BaseUser, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50)
    age = models.PositiveIntegerField(_("Age"), default=18)
    photo = models.ImageField(_("Photo"), upload_to="teacher/photos/", blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    categories = models.ManyToManyField(CategoriesOfStudents, related_name="teachers")
    teaching_experience = models.PositiveIntegerField(_("Teaching experience (years)"))
    about_me = models.TextField(_("About me"), blank=True)
    hobbies = models.TextField(_("Hobbies"), blank=True)
    education = models.TextField(_("Education"), blank=True)
    lesson_flow = models.TextField(_("Lesson flow"), blank=True)
    lesson_price = models.DecimalField(
        _("Lesson price (UAH)"), max_digits=8, decimal_places=2
    )
    lesson_duration = models.PositiveIntegerField(_("Lesson duration (minutes)"))
    subjects = models.ManyToManyField(Subject, related_name="teachers")
    telegram = models.CharField(_("Telegram"), max_length=100, blank=True, null=True)
    whatsapp = models.CharField(_("Whatsapp"), max_length=100, blank=True, null=True)
    viber = models.CharField(_("Viber"), max_length=100, blank=True, null=True)
    instagram = models.CharField(_("Instagram"), max_length=100, blank=True, null=True)
    is_verified = models.BooleanField(_("Verified"), default=False)
    rating = models.FloatField(_("Rating"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Student(models.Model):
    user = models.OneToOneField(
        BaseUser, on_delete=models.CASCADE, related_name="student_profile"
    )

    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50)
    age = models.PositiveIntegerField(_("Age"), default=18)
    phone = models.CharField(_("Phone"), max_length=20, blank=True, null=True)
    photo = models.ImageField(_("Photo"), upload_to="student/photos/", blank=True)

    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
