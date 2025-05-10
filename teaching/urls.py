from django.urls import path, include
from rest_framework.routers import DefaultRouter

from teaching import views

router = DefaultRouter()


router.register(r"schedules", views.ScheduleViewSet, basename="schedule")
router.register(r"lessons", views.LessonViewSet, basename="lesson")
router.register(r"ratings", views.RatingViewSet, basename="rating")
router.register(
    r"notifications", views.InternalNotificationViewSet, basename="notification"
)

extra_urlpatterns = [
    path("my-students/", views.MyStudentsView.as_view(), name="my-students"),
    path(
        "teachers/<int:teacher_id>/subjects/",
        views.TeacherSubjectListView.as_view(),
        name="teacher-subjects",
    ),
    path(
        "teachers/<int:teacher_id>/availability/",
        views.TeacherAvailabilityView.as_view(),
        name="teacher-availability",
    ),
]

urlpatterns = [
    path("", include(router.urls)),
    path("", include(extra_urlpatterns)),
]
