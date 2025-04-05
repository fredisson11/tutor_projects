from django.urls import path
from applications.views import TeacherApplicationCreateView

urlpatterns = [
    path("", TeacherApplicationCreateView.as_view(), name="teacher-application-create"),
]
