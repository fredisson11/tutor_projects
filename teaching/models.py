import os
import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

from django.db import models, transaction
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class Schedule(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="schedules"
    )
    schedule_start_time = models.TimeField()
    schedule_end_time = models.TimeField()

    class Meta:
        unique_together = ("teacher", "schedule_start_time")
        ordering = ["schedule_start_time"]

    def __str__(self):
        return f"{self.teacher} | {self.schedule_start_time}-{self.schedule_end_time}"


class Appointment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_appointments",
    )
    schedule = models.ForeignKey(
        Schedule, on_delete=models.CASCADE, related_name="appointments"
    )
    appointment_start_time = models.TimeField()
    appointment_end_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", _("Очікує")),
            ("confirmed", _("Підтверджено")),
            ("canceled", _("Скасовано")),
            ("completed", _("Завершено")),
        ],
        default="pending",
    )
    google_meet_link = models.URLField(blank=True, null=True)
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField()

    class Meta:
        unique_together = ("student", "schedule")

    def __str__(self):
        return f"{self.student} записаний до {self.teacher} на {self.date} {self.schedule.schedule_start_time}"

    def create_google_calendar_event(self):
        """Створюємо подію в Google Calendar"""
        creds = None
        if os.path.exists("token.json"):
            creds = google.auth.load_credentials_from_file("token.json")[0]

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", ["https://www.googleapis.com/auth/calendar"]
                )
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": f"Заняття: {self.teacher.first_name} {self.teacher.last_name}",
            "location": "Онлайн",
            "description": "Заняття для студентів",
            "start": {
                "dateTime": f"{self.date}T{self.appointment_start_time}",
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": f"{self.date}T{self.appointment_end_time}",
                "timeZone": "UTC",
            },
            "attendees": [
                {"email": self.teacher.email},
                {"email": self.student.email},
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": str(self.id),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    "status": {"statusCode": "success"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30},
                ]
            },
        }

        event_result = (
            service.events()
            .insert(calendarId="primary", body=event, conferenceDataVersion=1)
            .execute()
        )

        self.google_calendar_event_id = event_result["id"]
        self.save()
        return event_result["hangoutLink"]

    def save(self, *args, **kwargs):
        if not self.id:
            google_meet_link = self.create_google_calendar_event()
            self.google_meet_link = google_meet_link
        super().save(*args, **kwargs)

    @classmethod
    def create_appointment(cls, student, schedule):
        with transaction.atomic():
            appointment = cls.objects.create(
                student=student,
                teacher=schedule.teacher,
                schedule=schedule,
            )
        return appointment


class Rating(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_ratings",
    )
    score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} -> {self.teacher}: {self.score}"


class InternalNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    message_type = models.CharField(
        max_length=50,
        choices=[
            ("lesson_reminder_teacher", _("Нагадування для вчителя")),
            ("lesson_reminder_student", _("Нагадування для студента")),
            ("appointment_confirmed", _("Підтвердження запису")),
            ("appointment_canceled", _("Скасування запису")),
        ],
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user} - {self.message_type}"

    def mark_as_read(self):
        """Метод для позначення сповіщення як прочитане."""
        self.is_read = True
        self.save()
