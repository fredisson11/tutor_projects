from django.test import TestCase
from teaching.models import Appointment, Schedule
from django.contrib.auth import get_user_model
import google.auth
from unittest.mock import patch


class GoogleCalendarTest(TestCase):
    @patch("teaching.models.build")
    def test_create_google_calendar_event(self, mock_build):
        # Створюємо тестових користувачів
        teacher = get_user_model().objects.create_user(
            email="teacher@example.com", password="password"
        )
        student = get_user_model().objects.create_user(
            email="student@example.com", password="password"
        )

        # Створюємо тестовий розклад
        schedule = Schedule.objects.create(
            teacher=teacher,
            schedule_start_time="10:00:00",
            schedule_end_time="11:00:00",
        )

        # Створюємо тестову запис
        appointment = Appointment.create_appointment(student=student, schedule=schedule)

        # Перевірка, чи викликалось створення події через Google Calendar API
        self.assertTrue(mock_build.called)

        # Перевірка створення посилання Google Meet
        self.assertIsNotNone(appointment.google_meet_link)
