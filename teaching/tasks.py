from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from teaching.models import Appointment, InternalNotification, Schedule


@shared_task
def send_lesson_reminders():
    """Надсилає нагадування за 30 хвилин до початку уроку"""
    now = timezone.now()
    thirty_minutes_before = now + timedelta(minutes=30)

    schedules = Schedule.objects.filter(
        date=thirty_minutes_before.date(), start_time=thirty_minutes_before.time()
    )

    for schedule in schedules:
        InternalNotification.objects.create(
            user=schedule.teacher,
            message_type="lesson_reminder_teacher",
            message=f"Нагадування: Ваше заняття почнеться о {schedule.start_time}.",
        )

        appointments = Appointment.objects.filter(schedule=schedule)
        for appointment in appointments:
            InternalNotification.objects.create(
                user=appointment.student,
                message_type="lesson_reminder_student",
                message=f"Нагадування: Ваше заняття з {schedule.teacher.first_name} {schedule.teacher.last_name} "
                f"почнеться о {schedule.start_time}.",
            )
