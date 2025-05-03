# user/models.py

from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _


# --- Довідники --- #

class City(models.Model):
    name = models.CharField(_("City"), max_length=100, unique=True)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(_("Subject"), max_length=100, unique=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Subject")
        verbose_name_plural = _("Subjects")

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(_("Language"), max_length=100, unique=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")

    def __str__(self):
        return self.name


class CategoriesOfStudents(models.Model):
    CATEGORY_CHOICES = [
        ("preschooler", _("Preschooler")),
        ("1-4", _("Grades 1‑4")),
        ("5-8", _("Grades 5‑8")),
        ("9-12", _("Grades 9‑12")),
        ("adult", _("Adult")),
    ]
    # Збільшено max_length
    name = models.CharField(
        _("Category"), max_length=15, choices=CATEGORY_CHOICES, unique=True
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Category of students")
        verbose_name_plural = _("Categories of students")

    def __str__(self):
        return self.get_name_display()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("The email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", None)

        if not extra_fields["is_staff"]:
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields["is_superuser"]:
            raise ValueError(_("Superuser must have is_superuser=True."))

        extra_fields.setdefault("is_active", True)

        return self._create_user(email, password, **extra_fields)


class BaseUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("Email"), unique=True)
    is_active = models.BooleanField(_("Active"), default=False)
    is_staff = models.BooleanField(_("Staff status"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLES_CHOICES = [
        (ROLE_STUDENT, _("Student")),
        (ROLE_TEACHER, _("Teacher")),
    ]
    role = models.CharField(_("Role"), max_length=10, choices=ROLES_CHOICES, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.email


class Teacher(models.Model):
    user = models.OneToOneField(BaseUser, on_delete=models.CASCADE, related_name="teacher_profile")
    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50)
    age = models.PositiveIntegerField(_("Age"), null=True, blank=True)

    languages = models.ManyToManyField(Language, verbose_name=_("Languages"), blank=True)
    phone = models.CharField(_("Phone"), max_length=20, blank=True, null=True)
    photo = models.BinaryField(_("Photo"), null=True, blank=True)
    photo_format = models.CharField(_("Photo format"), max_length=10, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    categories = models.ManyToManyField(CategoriesOfStudents, related_name="teachers", blank=True)
    teaching_experience = models.PositiveIntegerField(_("Teaching experience (years)"), null=True, blank=True)
    about_me = models.TextField(_("About me"), blank=True)
    hobbies = models.TextField(_("Hobbies"), blank=True)
    education = models.TextField(_("Education"), blank=True)
    lesson_flow = models.TextField(_("Lesson flow"), blank=True)
    lesson_price = models.DecimalField(_("Lesson price (UAH)"), max_digits=8, decimal_places=2, null=True, blank=True)
    subjects = models.ManyToManyField(Subject, related_name="teachers", blank=True)
    telegram = models.CharField(_("Telegram"), max_length=100, blank=True, null=True)
    whatsapp = models.CharField(_("WhatsApp"), max_length=100, blank=True, null=True)
    viber = models.CharField(_("Viber"), max_length=100, blank=True, null=True)
    instagram = models.CharField(_("Instagram"), max_length=100, blank=True, null=True)
    is_verified = models.BooleanField(_("Verified"), default=False)
    is_qualified = models.BooleanField(_("Qualified"), default=False)

    # кешування рейтингу
    # average_rating = models.FloatField(_("Average Rating"), default=0.0)
    # rating_count = models.PositiveIntegerField(_("Rating Count"), default=0)

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Teacher")
        verbose_name_plural = _("Teachers")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Student(models.Model):
    user = models.OneToOneField(BaseUser, on_delete=models.CASCADE, related_name="student_profile")
    first_name = models.CharField(_("First name"), max_length=50, blank=True)
    last_name = models.CharField(_("Last name"), max_length=50, blank=True)
    phone = models.CharField(_("Phone"), max_length=20, blank=True, null=True)
    photo = models.BinaryField(_("Photo"), null=True, blank=True)
    photo_format = models.CharField(_("Photo format"), max_length=10, null=True, blank=True)

    class Meta:
        verbose_name = _("Student")
        verbose_name_plural = _("Students")

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.user.email
