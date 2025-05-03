from rest_framework import permissions
from user.models import BaseUser


class IsTeacher(permissions.BasePermission):
    """
    Дозвіл для перевірки, чи є користувач вчителем.
    """

    message = "Доступ дозволено лише для вчителів."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == BaseUser.ROLE_TEACHER
        )


class IsStudent(permissions.BasePermission):
    """
    Дозвіл для перевірки, чи є користувач студентом.
    """

    message = "Доступ дозволено лише для студентів."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == BaseUser.ROLE_STUDENT
        )


class IsProfileOwner(permissions.BasePermission):
    """
    Дозволяє доступ тільки власнику профілю (Teacher або Student).
    """

    message = "Ви не маєте дозволу на редагування цього профілю."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
