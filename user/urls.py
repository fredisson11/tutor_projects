from django.urls import path

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
    # Публічні ендпоінти для вчителів
    path("teachers/", TeacherListView.as_view(), name="teacher-list"),
    path("teachers/<int:pk>/", TeacherDetailView.as_view(), name="teacher-detail"),
    # --- Реєстрація та Активація ---
    path("register/", UserRegistrationView.as_view(), name="register"),
    # <str:token> для JWT токена
    path(
        "activate/<str:token>/", ActivateAccountView.as_view(), name="activate-account"
    ),

    # Створення профілю вчителя після реєстрації та активації
    path(
        "profile/teacher/complete/",
        CompleteTeacherProfileView.as_view(),
        name="complete-teacher-profile",
    ),
    # Перегляд та редагування власного профілю вчителя
    path(
        "profile/teacher/me/", TeacherProfileMeView.as_view(), name="teacher-profile-me"
    ),
    # Перегляд та редагування власного профілю студента
    path(
        "profile/student/me/", StudentProfileMeView.as_view(), name="student-profile-me"
    ),

    # Зміна пароля для аутент. користувача
    path(
        "auth/password/change/",
        ChangePasswordView.as_view(),
        name="password-change",
    ),
    # Запит скид. psswrd
    path(
        "auth/password/reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    # Підтвердження скидання пароля (токен передається в тілі запиту, не в URL)
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
