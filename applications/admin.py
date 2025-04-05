from django.contrib import admin
from applications.models import TeacherApplication


@admin.register(TeacherApplication)
class TeacherApplicationAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "specialty", "created_at")
    search_fields = ("first_name", "last_name", "email")
    list_filter = ("specialty", "created_at")
