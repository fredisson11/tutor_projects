from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.timezone import now
from django.shortcuts import get_object_or_404

from teaching.models import Schedule, Appointment, Rating, InternalNotification
from teaching.serializers import (
    ScheduleSerializer,
    AppointmentSerializer,
    RatingSerializer,
    InternalNotificationSerializer,
)
from teaching.permissions import IsTeacher, IsStudent


class ScheduleViewSet(viewsets.ModelViewSet):
    """API для перегляду та створення розкладів викладачів"""
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get_queryset(self):
        return Schedule.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class AppointmentViewSet(viewsets.ModelViewSet):
    """API для перегляду та створення записів на заняття"""
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type == "student":
            return Appointment.objects.filter(student=self.request.user)
        elif self.request.user.user_type == "teacher":
            return Appointment.objects.filter(teacher=self.request.user)
        return Appointment.objects.none()

    def perform_create(self, serializer):
        schedule = get_object_or_404(Schedule, id=self.request.data["schedule"])
        student = self.request.user
        appointment = Appointment.create_appointment(student=student, schedule=schedule)
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsTeacher])
    def confirm(self, request, *args, **kwargs):
        """Підтвердити запис на заняття"""
        appointment = self.get_object()
        appointment.status = "confirmed"
        appointment.save()
        return Response({"message": "Заняття підтверджено"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsTeacher])
    def complete(self, request, *args, **kwargs):
        """Завершити заняття"""
        appointment = self.get_object()
        if appointment.status != "confirmed":
            return Response(
                {"error": "Заняття не підтверджено"}, status=status.HTTP_400_BAD_REQUEST
            )

        if now() < appointment.schedule.end_time:
            return Response(
                {"error": "Заняття ще не закінчилось"}, status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = "completed"
        appointment.save()
        return Response({"message": "Заняття завершено"}, status=status.HTTP_200_OK)


class RatingViewSet(viewsets.ModelViewSet):
    """API для створення та перегляду оцінок викладачів"""
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Rating.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class InternalNotificationViewSet(viewsets.ModelViewSet):
    """API для перегляду та керування сповіщеннями"""
    serializer_class = InternalNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InternalNotification.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def mark_as_read(self, request, *args, **kwargs):
        """Позначити сповіщення як прочитане"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({"message": "Сповіщення позначене як прочитане"}, status=status.HTTP_200_OK)


class ScheduleListCreateView(generics.ListCreateAPIView):
    """API для перегляду та створення розкладів"""
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get_queryset(self):
        return Schedule.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class AppointmentCreateView(generics.CreateAPIView):
    """API для створення запису на заняття"""
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def perform_create(self, serializer):
        schedule = get_object_or_404(Schedule, id=self.request.data["schedule"])
        student = self.request.user
        appointment = Appointment.create_appointment(student=student, schedule=schedule)
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)
