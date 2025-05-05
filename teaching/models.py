from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta

from user.models import Student, Teacher, Subject, BaseUser, CategoriesOfStudents


class Schedule(models.Model):
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="schedules"
    )

    WEEKDAYS = [
        ("monday", _("Monday")),
        ("tuesday", _("Tuesday")),
        ("wednesday", _("Wednesday")),
        ("thursday", _("Thursday")),
        ("friday", _("Friday")),
        ("saturday", _("Saturday")),
        ("sunday", _("Sunday")),
    ]
    weekday = models.CharField(_("Weekday"), max_length=10, choices=WEEKDAYS)
    start_time = models.TimeField(_("Start time"))
    end_time = models.TimeField(_("End time"))
    created_at = models.DateTimeField(
        _("Created at"), auto_now_add=True, null=True
    )

    class Meta:
        verbose_name = _("Schedule")
        verbose_name_plural = _("Schedules")
        unique_together = ("teacher", "weekday", "start_time", "end_time")
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return (
            f"{self.teacher.first_name}'s schedule on "
            f"{self.get_weekday_display()} from "
            f"{self.start_time} to {self.end_time}"
        )


class LessonStatus(models.TextChoices):
    VOID = "void", _("Pending Confirmation")
    APPROVED = "approved", _("Approved")
    CANCELLED_BY_TEACHER = "cancelled_by_teacher", _("Cancelled by Teacher")
    CANCELLED_BY_STUDENT = "cancelled_by_student", _("Cancelled by Student")
    DONE = "done", _("Done")


class Lesson(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="lessons"
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="lessons"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="lessons"
    )
    category = models.ForeignKey(
        CategoriesOfStudents,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
        verbose_name=_("Student Category"),
    )
    start_time = models.DateTimeField(_("Start time"))
    end_time = models.DateTimeField(_("End time"), null=True, blank=True)
    homework = models.TextField(_("Homework"), blank=True, null=True)
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=LessonStatus.choices,
        default=LessonStatus.VOID,
    )
    is_paid = models.BooleanField(_("Paid"), default=False)
    google_meet_link = models.URLField(
        _("Google Meet Link"), max_length=255, blank=True, null=True
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Lesson")
        verbose_name_plural = _("Lessons")
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["teacher", "start_time", "end_time"]),
            models.Index(fields=["student", "start_time", "end_time"]),
        ]

    def __str__(self):
        end_time_str = f" - {self.end_time.strftime('%H:%M')}" if self.end_time else ""
        category_str = f" ({self.category})" if self.category else ""
        return (
            f"{self.subject.name}{category_str} | "
            f"{self.teacher.first_name} - "
            f"{self.student.first_name} | "
            f"{self.start_time.strftime('%Y-%m-%d %H:%M')}{end_time_str}"
        )

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return timedelta(hours=1)

    def save(self, *args, **kwargs):
        if self.start_time and not self.end_time:
            super().save(*args, **kwargs)

    def is_reviewable(self):
        return self.status == LessonStatus.DONE

    def add_homework(self, homework_text):
        self.homework = homework_text
        self.save(update_fields=["homework"])

    def update_status_if_expired(self):
        now = timezone.now()
        expired = False
        if self.end_time and now > self.end_time:
            expired = True
        elif not self.end_time and now > (
            self.start_time + timedelta(hours=1)
        ):
            expired = True

        if expired and self.status in [LessonStatus.VOID, LessonStatus.APPROVED]:
            self.status = LessonStatus.DONE
            self.save(update_fields=["status"])

    def create_google_meet(self):
        # Цей метод має викликати фонове завдання Celery
        # from .tasks import generate_google_meet_task
        # generate_google_meet_task.delay(self.id)
        print(
            f"Task to create Google Meet for Lesson {self.id} should be triggered here."
        )
        pass


class InternalNotification(models.Model):
    user = models.ForeignKey(
        BaseUser, on_delete=models.CASCADE, related_name="notifications"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.TextField(_("Message"))
    is_read = models.BooleanField(_("Read"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Internal Notification")
        verbose_name_plural = _("Internal Notifications")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification to {self.user.email}: {self.message[:50]}..."


class Rating(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="given_ratings"
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="ratings"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="ratings"
    )
    rating = models.PositiveSmallIntegerField(
        _("Rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=1,
    )
    comment = models.TextField(_("Comment"), blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Rating")
        verbose_name_plural = _("Ratings")
        unique_together = ("student", "lesson")
        ordering = ["-created_at"]

    def __str__(self):
        lesson_info = f" for Lesson {self.lesson.id}" if self.lesson else ""
        return f"{self.student.first_name} rated {self.teacher.first_name}: {self.rating}/5{lesson_info}"
