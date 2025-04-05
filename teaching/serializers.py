from rest_framework import serializers
from teaching.models import Schedule, Appointment, Rating, InternalNotification


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = [
            "id",
            "teacher",
            "schedule_start_time",
            "schedule_end_time",
        ]
        read_only_fields = []


class AppointmentSerializer(serializers.ModelSerializer):
    student = serializers.ReadOnlyField(source="student.id")
    google_meet_link = serializers.URLField(read_only=True)
    teacher = serializers.ReadOnlyField(source="teacher.id")
    schedule = serializers.PrimaryKeyRelatedField(queryset=Schedule.objects.all())

    class Meta:
        model = Appointment
        fields = [
            "id",
            "student",
            "teacher",
            "schedule",
            "appointment_start_time",
            "appointment_end_time",
            "status",
            "google_meet_link",
            "date",
        ]

    def validate(self, data):
        schedule = data.get("schedule")
        if Appointment.objects.filter(
            schedule=schedule, status__in=["pending", "confirmed"]
        ).exists():
            raise serializers.ValidationError("Цей час уже заброньовано.")
        return data


class RatingSerializer(serializers.ModelSerializer):
    student = serializers.ReadOnlyField(source="student.id")
    teacher = serializers.ReadOnlyField(source="teacher.id")

    class Meta:
        model = Rating
        fields = ["id", "student", "teacher", "score", "comment", "created_at"]
        read_only_fields = ["created_at"]


class InternalNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalNotification
        fields = ["id", "message_type", "message", "created_at", "is_read"]
        read_only_fields = ["id", "message_type", "message", "created_at"]

    def update(self, instance, validated_data):
        # Дозволяємо оновлювати лише поле `is_read`
        instance.is_read = validated_data.get("is_read", instance.is_read)
        instance.save()
        return instance

