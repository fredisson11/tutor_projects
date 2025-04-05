from django.contrib import admin
from .models import BaseUser, Student, Teacher, Specialty
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _


@admin.register(BaseUser)
class CustomUserAdmin(UserAdmin):
    model = BaseUser
    list_display = ("email", "first_name", "last_name", "user_type", "is_active")
    list_filter = ("user_type", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Персональна інформація"), {"fields": ("first_name", "last_name", "age", "bio", "rating", "user_type")}),
        (_("Права доступу"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2", "user_type"),
        }),
    )


admin.site.register(Student)
admin.site.register(Teacher)
admin.site.register(Specialty)
