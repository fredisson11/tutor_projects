from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from django.conf import settings
from django.conf.urls.static import static


from user.views import (
    RegisterUserView,
    ActivateAccountView,
    TeacherProfileView,
    StudentProfileView,
)

app_name = "user"

urlpatterns = [
    path(
        "register/", RegisterUserView.as_view(), name="register_user"
    ),
    path(
        "activate/<str:token>/", ActivateAccountView.as_view(), name="activate_account"
    ),
    path(
        "profile/student/<int:user_id>/",
        StudentProfileView.as_view(),
        name="student_profile",
    ),
    path(
        "profile/teacher/<int:user_id>/",
        TeacherProfileView.as_view(),
        name="teacher_profile",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
