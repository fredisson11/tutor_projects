from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Перевірка, чи є користувач вчителем.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and hasattr(request.user, "is_teacher")
            and request.user.is_teacher
        )


class IsStudent(permissions.BasePermission):
    """
    Перевірка, чи є користувач студентом.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and hasattr(request.user, "is_student")
            and request.user.is_student
        )
