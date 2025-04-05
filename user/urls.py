from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from user.views import (
    RegisterStudentAPIView,
    RegisterTeacherAPIView,
    ActivateAccountAPIView,
    LoginAPIView,
    StudentMeAPIView,
    TeacherMeAPIView,
    ChangePasswordAPIView,
)

app_name = "user"

urlpatterns = [
    path("register/student/", RegisterStudentAPIView.as_view(), name="register_student"),
    path("register/teacher/", RegisterTeacherAPIView.as_view(), name="register_teacher"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("me/student/", StudentMeAPIView.as_view(), name="student_me"),
    path("me/teacher/", TeacherMeAPIView.as_view(), name="teacher_me"),
    path("api/activate/<str:uidb64>/<str:token>/", ActivateAccountAPIView.as_view(), name="activate"),
    path("api/login/", LoginAPIView.as_view(), name="login"),
    path("me/student/change-password/", ChangePasswordAPIView.as_view(), name="student_change_password"),
    path("me/teacher/change-password/", ChangePasswordAPIView.as_view(), name="teacher_change_password"),
]
