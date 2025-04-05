from django.urls import path
from rest_framework.routers import DefaultRouter
from teaching.views import (
    ScheduleListCreateView,
    AppointmentCreateView,
    AppointmentViewSet,
    InternalNotificationViewSet,
)

router = DefaultRouter()
router.register(r"appointments", AppointmentViewSet, basename="appointments")
router.register(r"notifications", InternalNotificationViewSet, basename="notifications")

urlpatterns = [
    path(
        "schedules/",
        ScheduleListCreateView.as_view(),
        name="schedule-list-create",
    ),
    path(
        "appointments/create/<int:schedule_id>/",
        AppointmentCreateView.as_view(),
        name="appointment-create",
    ),
]

urlpatterns += router.urls
