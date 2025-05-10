from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from teaching.models import Lesson, Schedule, InternalNotification, Rating, LessonStatus


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "teacher",
        "subject",
        "category",
        "start_time",
        "end_time",
        "status",
        "is_paid",
        "google_meet_link",
        "created_at",
    )
    list_filter = ("status", "is_paid", "teacher", "student", "subject", "category")
    search_fields = (
        "id",
        "student__first_name",
        "student__last_name",
        "teacher__first_name",
        "teacher__last_name",
        "subject__name",
        "category__name",
    )
    readonly_fields = ("created_at", "end_time")
    list_editable = ("is_paid", "status")
    date_hierarchy = "start_time"
    list_select_related = ("student", "teacher", "subject", "category")

    actions = ["mark_as_done", "mark_as_approved", "create_google_meet_links_action"]

    @admin.action(description=_("Mark selected lessons as Done"))
    def mark_as_done(self, request, queryset):
        updated_count = queryset.update(status=LessonStatus.DONE)
        self.message_user(request, f"{updated_count} уроків позначено як Завершені.")

    @admin.action(description=_("Mark selected lessons as Approved"))
    def mark_as_approved(self, request, queryset):
        updated_count = queryset.filter(status=LessonStatus.VOID).update(
            status=LessonStatus.APPROVED
        )
        self.message_user(request, f"{updated_count} уроків позначено як Підтверджені.")

    @admin.action(description=_("Try to create Google Meet links for selected lessons"))
    def create_google_meet_links_action(self, request, queryset):
        count_success = 0
        count_failed = 0
        lessons_to_process = queryset.filter(
            google_meet_link__isnull=True,
            status__in=[LessonStatus.VOID, LessonStatus.APPROVED],
        )
        for lesson in lessons_to_process:
            try:
                if hasattr(lesson, "create_google_meet"):
                    created = lesson.create_google_meet()
                    if created:
                        count_success += 1
                else:
                    self.message_user(
                        request,
                        f"Метод create_google_meet не знайдено для уроку {lesson.id}",
                        level="WARNING",
                    )
                    count_failed += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Помилка при створенні Meet для уроку {lesson.id}: {e}",
                    level="ERROR",
                )
                count_failed += 1
        if count_success > 0:
            self.message_user(
                request,
                f"Завдання на створення посилання Google Meet запущено для {count_success} уроків.",
            )
        if count_failed > 0:
            self.message_user(
                request,
                f"Не вдалося запустити завдання для {count_failed} уроків.",
                level="WARNING",
            )


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "teacher", "weekday", "start_time", "end_time", "created_at")
    list_filter = ("teacher", "weekday")
    search_fields = (
        "teacher__first_name",
        "teacher__last_name",
    )
    ordering = ("teacher", "weekday", "start_time")
    readonly_fields = ("created_at",)
    list_select_related = ("teacher",)


@admin.register(InternalNotification)
class InternalNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "lesson_info",
        "message_short",
        "is_read",
        "created_at",
    )
    list_filter = ("is_read", "user")
    search_fields = (
        "user__email",
        "lesson__id",
        "message",
    )
    readonly_fields = ("created_at", "user", "lesson", "message")
    list_display_links = ("id", "message_short")
    list_select_related = ("user", "lesson")

    @admin.display(description="Lesson")
    def lesson_info(self, obj):
        if obj.lesson:
            link = reverse("admin:teaching_lesson_change", args=[obj.lesson.id])
            return format_html('<a href="{}">{}</a>', link, obj.lesson)
        return "-"

    lesson_info.admin_order_field = "lesson"

    @admin.display(description="Message")
    def message_short(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "teacher", "lesson_link", "rating", "created_at")
    list_filter = ("rating", "teacher", "student")
    search_fields = (
        "student__first_name",
        "student__last_name",
        "teacher__first_name",
        "teacher__last_name",
        "lesson__id",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "student", "teacher", "lesson")
    list_select_related = ("student", "teacher", "lesson")

    @admin.display(description="Lesson")
    def lesson_link(self, obj):
        if obj.lesson:
            link = reverse("admin:teaching_lesson_change", args=[obj.lesson.id])
            return format_html('<a href="{}">{}</a>', link, obj.lesson)
        return "-"

    lesson_link.admin_order_field = "lesson"
