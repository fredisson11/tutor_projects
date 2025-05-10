from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from user.views import (
    UserRegistrationView,
    CityListView,
    SubjectListView,
    TeacherListView,
    TeacherDetailView,
    ActivateAccountView,
    CompleteTeacherProfileView,
    LanguageListView,
    CategoriesOfStudentsListView,
    TeacherProfileMeView,
    StudentProfileMeView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserLoginView,
)

app_name = "user"

urlpatterns = [
    path("cities/", CityListView.as_view(), name="city-list"),
    path("subjects/", SubjectListView.as_view(), name="subject-list"),
    path("languages/", LanguageListView.as_view(), name="language-list"),
    path(
        "student-categories/",
        CategoriesOfStudentsListView.as_view(),
        name="student-category-list",
    ),
    path("teachers/", TeacherListView.as_view(), name="teacher-list"),
    path("teachers/<int:pk>/", TeacherDetailView.as_view(), name="teacher-detail"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path(
        "activate/<str:token>/", ActivateAccountView.as_view(), name="activate-account"
    ),
    path(
        "profile/teacher/complete/",
        CompleteTeacherProfileView.as_view(),
        name="complete-teacher-profile",
    ),
    path(
        "profile/teacher/me/", TeacherProfileMeView.as_view(), name="teacher-profile-me"
    ),
    path(
        "profile/student/me/", StudentProfileMeView.as_view(), name="student-profile-me"
    ),

    path("auth/login/", UserLoginView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/password/change/", ChangePasswordView.as_view(), name="password-change"),
    path(
        "auth/password/reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
