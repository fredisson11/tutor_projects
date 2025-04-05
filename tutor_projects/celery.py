from celery import Celery
from celery.schedules import crontab

app = Celery("tutor_projects")

app.conf.beat_schedule = {
    "send_lesson_reminders_every_5_minutes": {
        "task": "tutor_projects.tasks.send_lesson_reminders",
        "schedule": crontab(minute="*/5")
    },
}
