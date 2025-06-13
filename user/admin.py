from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    BaseUser,
    Teacher,
    Student,
    City,
    Subject,
    Language,
    CategoriesOfStudents,
)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "id")
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at",)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at",)


@admin.register(CategoriesOfStudents)
class CategoriesOfStudentsAdmin(admin.ModelAdmin):
    list_display = ("name", "get_name_display", "id", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at",)
    list_display_links = ("name", "get_name_display")


@admin.register(BaseUser)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "role", "groups")
    search_fields = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("role",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password",
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "created_at")


class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    verbose_name_plural = _("Teacher Profile")
    fk_name = "user"


class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = _("Student Profile")
    fk_name = "user"


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "user_link",
        "first_name",
        "last_name",
        "city",
        "teaching_experience",
        "is_verified",
        "created_at",
    )
    list_filter = (
        "is_verified",
        "city",
        "subjects",
        "categories",
        "languages",
    )
    search_fields = ("first_name", "last_name", "user__email", "phone")
    readonly_fields = ("created_at", "user", "photo")
    list_select_related = ("user", "city")
    filter_horizontal = ("languages", "categories", "subjects")
    raw_id_fields = (
        "user",
        "city",
    )
    list_editable = ("is_verified",)

    fieldsets = (
        (None, {"fields": ("user", ("first_name", "last_name"), "age")}),
        (
            _("Contact Info"),
            {"fields": ("phone", "city", "telegram", "whatsapp", "viber", "instagram")},
        ),
        (
            _("Professional Info"),
            {
                "fields": (
                    "teaching_experience",
                    "subjects",
                    "categories",
                    "languages",
                    "lesson_price",
                )
            },
        ),
        (
            _("Profile Details"),
            {"fields": ("about_me", "hobbies", "education", "lesson_flow")},
        ),
        (_("Status"), {"fields": ("is_verified",)}),
        (_("Photo"), {"fields": ("photo", "photo_format")}),
        (_("Dates"), {"fields": ("created_at",)}),
    )

    @admin.display(description=_("User"), ordering="user__email")
    def user_link(self, obj):
        if obj.user:
            link = reverse("admin:user_baseuser_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', link, obj.user.email)
        return "-"


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user_link", "first_name", "last_name", "phone")
    search_fields = ("first_name", "last_name", "user__email", "phone")
    readonly_fields = ("user", "photo")
    list_select_related = ("user",)
    raw_id_fields = ("user",)
    fields = ("user", "first_name", "last_name", "phone", "photo")

    @admin.display(description=_("User"), ordering="user__email")
    def user_link(self, obj):
        if obj.user:
            link = reverse("admin:user_baseuser_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', link, obj.user.email)
        return "-"
