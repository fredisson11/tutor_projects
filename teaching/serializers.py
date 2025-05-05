# teaching/serializers.py

from datetime import timedelta, datetime

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

# Імпортуємо МОДЕЛІ з user та teaching
try:
    from user.models import Student, Teacher, Subject, CategoriesOfStudents, BaseUser

    # Імпортуємо базові серіалайзери довідників з user
    from user.serializers import SubjectSerializer, CategoriesOfStudentsSerializer
except ImportError:
    raise ImportError(
        "Could not import models/serializers from 'user' app. Check your project structure and INSTALLED_APPS."
    )

try:
    from teaching.models import (
        Schedule,
        Lesson,
        Rating,
        InternalNotification,
        LessonStatus,
    )
except ImportError:
    raise ImportError("Could not import models from 'teaching' app.")


# --- Серіалайзери для представлення Студента/Вчителя в контексті Уроку ---
class LessonStudentSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Student
        fields = ["id", "first_name", "last_name", "phone", "email"]
        read_only_fields = fields


class LessonTeacherSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Teacher
        fields = ["id", "first_name", "last_name", "email"]
        read_only_fields = fields


# --- Серіалайзер для розкладу ---
class ScheduleSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.__str__", read_only=True)
    weekday_display = serializers.CharField(
        source="get_weekday_display", read_only=True
    )

    class Meta:
        model = Schedule
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "weekday",
            "weekday_display",
            "start_time",
            "end_time",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "teacher",
            "teacher_name",
            "weekday_display",
            "created_at",
        ]

    def validate(self, data):
        if (
            data.get("start_time")
            and data.get("end_time")
            and data["start_time"] >= data["end_time"]
        ):
            raise serializers.ValidationError(
                _("Start time must be earlier than end time.")
            )
        return data


# --- Серіалайзери для Уроків ---
class LessonListSerializer(serializers.ModelSerializer):
    student = LessonStudentSerializer(read_only=True)
    teacher = LessonTeacherSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    category = CategoriesOfStudentsSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "student",
            "teacher",
            "subject",
            "category",
            "start_time",
            "end_time",
            "status",
            "status_display",
            "is_paid",
            "google_meet_link",
        ]


class LessonDetailSerializer(serializers.ModelSerializer):
    student = LessonStudentSerializer(read_only=True)
    teacher = LessonTeacherSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    category = CategoriesOfStudentsSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source="student", write_only=True, required=True
    )
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), source="subject", write_only=True, required=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoriesOfStudents.objects.all(),
        source="category",
        write_only=True,
        required=True,
    )
    duration_hours = serializers.ChoiceField(
        choices=[1, 2],
        write_only=True,
        required=False,
        label=_("Duration (hours)"),
        default=1,
    )
    is_paid = serializers.BooleanField(required=False, default=False)
    homework = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "student",
            "teacher",
            "subject",
            "category",
            "student_id",
            "subject_id",
            "category_id",
            "start_time",
            "end_time",
            "duration_hours",
            "status",
            "status_display",
            "is_paid",
            "homework",
            "google_meet_link",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "teacher",
            "subject",
            "category",
            "status_display",
            "google_meet_link",
            "created_at",
            "end_time",
            "status",
        ]

    @staticmethod
    def validate_start_time(value):
        if value < timezone.now():
            raise serializers.ValidationError(
                _("Cannot schedule a lesson in the past.")
            )
        if value.minute != 0 or value.second != 0 or value.microsecond != 0:
            raise serializers.ValidationError(
                _("Lessons must start exactly on the hour.")
            )
        return value

    def validate(self, data):
        if self.instance is not None:
            allowed_update_fields = {"is_paid", "homework"}
            if not set(data.keys()).issubset(allowed_update_fields):
                raise serializers.ValidationError(
                    _("Only 'is_paid' or 'homework' can be updated.")
                )
            return data

        request = self.context.get("request")
        user = request.user if request else None
        if not user or not user.is_authenticated:
            raise serializers.ValidationError(_("Authentication required."))

        start_time = data.get("start_time")
        duration_hours = data.get("duration_hours", 1)
        subject = data.get("subject")
        category = data.get("category")
        student = data.get("student")
        teacher = None
        is_created_by_teacher = (
            hasattr(user, "teacher_profile") and user.role == BaseUser.ROLE_TEACHER
        )
        is_created_by_student = (
            hasattr(user, "student_profile") and user.role == BaseUser.ROLE_STUDENT
        )

        if not is_created_by_teacher and not is_created_by_student:
            raise serializers.ValidationError(
                _("Invalid user role for creating lessons.")
            )

        if is_created_by_teacher:
            teacher = user.teacher_profile
            if not student:
                raise serializers.ValidationError(
                    {"student_id": _("Student is required when booking by teacher.")}
                )
        elif is_created_by_student:
            student = user.student_profile
            teacher_id = self.context.get("request").data.get("teacher_id")
            if not teacher_id:
                raise serializers.ValidationError(
                    {
                        "teacher_id": _(
                            "Teacher must be specified when booking by student."
                        )
                    }
                )
            try:
                teacher = Teacher.objects.get(id=teacher_id)
                data["teacher"] = teacher
            except Teacher.DoesNotExist:
                raise serializers.ValidationError(
                    {"teacher_id": _("Invalid teacher selected.")}
                )

        if not teacher:
            raise serializers.ValidationError(
                _("Could not determine the teacher for the lesson.")
            )
        if not all([start_time, duration_hours, student, subject, category]):
            raise serializers.ValidationError(_("Missing required fields for booking."))

        end_time = start_time + timedelta(hours=duration_hours)
        data["end_time"] = end_time

        if subject not in teacher.subjects.all():
            raise serializers.ValidationError(
                _("This teacher does not teach the selected subject.")
            )
        if category not in teacher.categories.all():
            raise serializers.ValidationError(
                _("This teacher does not work with the selected student category.")
            )

        overlapping_lessons = Lesson.objects.filter(
            teacher=teacher,
            status__in=[LessonStatus.VOID, LessonStatus.APPROVED],
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if overlapping_lessons.exists():
            raise serializers.ValidationError(
                _(
                    "The selected time slot overlaps with another lesson for this teacher."
                )
            )

        lesson_day_name = start_time.strftime("%A").lower()
        lesson_start_time = start_time.time()
        lesson_end_time = end_time.time()

        if lesson_end_time <= lesson_start_time:
            schedule_part1 = Schedule.objects.filter(
                teacher=teacher,
                weekday=lesson_day_name,
                start_time__lte=lesson_start_time,
                end_time=datetime.strptime("23:59:59", "%H:%M:%S").time(),
            ).exists()
            next_day_index = (start_time.weekday() + 1) % 7
            next_day_name = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ][next_day_index]
            schedule_part2 = Schedule.objects.filter(
                teacher=teacher,
                weekday=next_day_name,
                start_time=datetime.strptime("00:00:00", "%H:%M:%S").time(),
                end_time__gte=lesson_end_time,
            ).exists()
            if not (schedule_part1 and schedule_part2):
                raise serializers.ValidationError(
                    _(
                        "The selected time slot (crossing midnight) does not fit within the teacher's available "
                        "schedule."
                    )
                )
        else:
            schedule_exists = Schedule.objects.filter(
                teacher=teacher,
                weekday=lesson_day_name,
                start_time__lte=lesson_start_time,
                end_time__gte=lesson_end_time,
            ).exists()
            if not schedule_exists:
                if duration_hours == 2:
                    first_hour_schedule = Schedule.objects.filter(
                        teacher=teacher,
                        weekday=lesson_day_name,
                        start_time__lte=lesson_start_time,
                        end_time__gte=(start_time + timedelta(hours=1)).time(),
                    ).exists()
                    second_hour_schedule = Schedule.objects.filter(
                        teacher=teacher,
                        weekday=lesson_day_name,
                        start_time__lte=(start_time + timedelta(hours=1)).time(),
                        end_time__gte=lesson_end_time,
                    ).exists()
                    if not (first_hour_schedule and second_hour_schedule):
                        raise serializers.ValidationError(
                            _(
                                "The selected 2-hour slot does not fit within the teacher's available schedule."
                            )
                        )
                else:
                    raise serializers.ValidationError(
                        _(
                            "The selected time slot does not fit within the teacher's available schedule."
                        )
                    )

        if is_created_by_teacher:
            data["teacher"] = teacher
            data["student"] = student
        elif is_created_by_student:
            data["student"] = student
            data["teacher"] = teacher
        return data


class RatingSerializer(serializers.ModelSerializer):
    student = serializers.ReadOnlyField(source="student.id")
    teacher = serializers.ReadOnlyField(source="teacher.id")

    class Meta:
        model = Rating
        fields = ["id", "student", "teacher", "rating", "comment", "created_at"]
        read_only_fields = ["id", "student", "teacher", "created_at"]


class PublicRatingSerializer(serializers.ModelSerializer):
    student_first_name = serializers.CharField(
        source="student.first_name", read_only=True
    )

    class Meta:
        model = Rating
        fields = ["id", "rating", "comment", "created_at", "student_first_name"]
        read_only_fields = fields


class InternalNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalNotification
        fields = ["id", "user", "lesson", "message", "is_read", "created_at"]
        read_only_fields = ["id", "user", "lesson", "message", "created_at"]
        extra_kwargs = {"is_read": {"read_only": False}}


class MyStudentSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Student
        fields = ["id", "first_name", "last_name", "phone", "photo", "email"]
        read_only_fields = fields

    @staticmethod
    def get_photo(obj):
        try:
            from user.serializers import Base64ImageField

            return Base64ImageField().to_representation(obj)
        except ImportError:
            return None
