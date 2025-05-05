# teaching/views.py

import logging
from datetime import timedelta, datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from rest_framework import generics, status, viewsets, filters
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination

try:
    from user.models import Teacher, Student, BaseUser
    from user.permissions import IsTeacher, IsStudent, IsProfileOwner, DenyAll
except ImportError:
    raise ImportError("Could not import models/permissions from 'user' app.")

try:
    from teaching.models import (
        Schedule,
        Lesson,
        Rating,
        InternalNotification,
        LessonStatus,
    )
    from .serializers import (
        ScheduleSerializer,
        LessonListSerializer,
        LessonDetailSerializer,
        RatingSerializer,
        InternalNotificationSerializer,
        MyStudentSerializer,
    )
    from user.serializers import SubjectSerializer
except ImportError as e:
    raise ImportError(
        f"Could not import models/serializers from 'teaching' or 'user' app. Error: {e}"
    )


logger = logging.getLogger(__name__)


def generate_and_save_google_meet_link(lesson_instance):
    if not lesson_instance.google_meet_link:
        try:
            dummy_link = f"https://meet.google.com/lookup/{lesson_instance.id}-{lesson_instance.created_at.timestamp()}"
            lesson_instance.google_meet_link = dummy_link
            lesson_instance.save(update_fields=["google_meet_link"])
            logger.info(
                f"Generated dummy Google Meet link for lesson {lesson_instance.id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to generate Google Meet link for lesson {lesson_instance.id}: {e}"
            )
            return False
    return False


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = "page_size"
    max_page_size = 50


class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "teacher_profile"):
            return Schedule.objects.filter(teacher=user.teacher_profile)
        return Schedule.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, "teacher_profile"):
            raise PermissionDenied("Only teachers can create schedules.")
        teacher_profile = user.teacher_profile
        start_time = serializer.validated_data["start_time"]
        end_time = serializer.validated_data["end_time"]
        weekday = serializer.validated_data["weekday"]
        overlapping_schedules = Schedule.objects.filter(
            teacher=teacher_profile,
            weekday=weekday,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        action = getattr(self, "action", None)
        if action == "update" or action == "partial_update":
            overlapping_schedules = overlapping_schedules.exclude(
                pk=self.get_object().pk
            )
        if overlapping_schedules.exists():
            raise ValidationError(
                _("The new time slot overlaps with an existing one in your schedule.")
            )
        serializer.save(teacher=teacher_profile)

    def perform_update(self, serializer):
        self.perform_create(serializer)


class LessonViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action == "list":
            return LessonListSerializer
        return LessonDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Lesson.objects.select_related(
            "student",
            "teacher",
            "subject",
            "category",
            "student__user",
            "teacher__user",
        )
        if hasattr(user, "teacher_profile"):
            queryset = queryset.filter(teacher=user.teacher_profile)
        elif hasattr(user, "student_profile"):
            queryset = queryset.filter(student=user.student_profile)
        else:
            return Lesson.objects.none()

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        status_param = self.request.query_params.get("status")

        if date_from:
            try:
                queryset = queryset.filter(
                    start_time__gte=datetime.fromisoformat(date_from)
                )
            except ValueError:
                pass
        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to) + timedelta(days=1)
                queryset = queryset.filter(start_time__lt=date_to_dt)
            except ValueError:
                pass
        if status_param and status_param in LessonStatus.values:
            queryset = queryset.filter(status=status_param)

        return queryset.order_by("start_time")

    def get_permissions(self):
        action = getattr(self, "action", None)
        if action == "create":
            self.permission_classes = [IsAuthenticated, (IsStudent | IsTeacher)]
        elif action in ["update", "partial_update", "mark_paid", "add_homework"]:
            self.permission_classes = [IsAuthenticated, IsTeacher]
        elif action == "destroy":
            self.permission_classes = [DenyAll]
        elif action in ["cancel_lesson", "approve_lesson"]:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        teacher = None
        student = None
        is_paid_on_create = serializer.validated_data.get("is_paid", False)

        if hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            student = serializer.validated_data.get("student")
            if not student:
                raise ValidationError({"student_id": "Student is required."})
            lesson = serializer.save(
                teacher=teacher, student=student, is_paid=is_paid_on_create
            )
            logger.info(
                f"Lesson {lesson.id} created by TEACHER {teacher.user.email} for student {student.user.email}"
            )

        elif hasattr(user, "student_profile"):
            student = user.student_profile
            teacher = serializer.validated_data.get("teacher")
            if not teacher:
                raise ValidationError({"teacher_id": "Teacher is required."})
            lesson = serializer.save(student=student, teacher=teacher, is_paid=False)
            logger.info(
                f"Lesson {lesson.id} created by STUDENT {student.user.email} for teacher {teacher.user.email}"
            )
        else:
            raise PermissionDenied(
                "User must be a student or a teacher to create lessons."
            )

        generate_and_save_google_meet_link(lesson)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        action = getattr(self, "action", None)
        if action == "create" and hasattr(self.request.user, "student_profile"):
            teacher_id = self.request.data.get("teacher_id")
            if teacher_id:
                try:
                    context["teacher"] = Teacher.objects.get(id=teacher_id)
                except Teacher.DoesNotExist:
                    pass
        return context

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_lesson(self, request, pk=None):
        lesson = self.get_object()
        user = request.user

        if lesson.status not in [LessonStatus.VOID, LessonStatus.APPROVED]:
            return Response(
                {"error": _("Only pending or approved lessons can be cancelled.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cancel_deadline = getattr(settings, "LESSON_CANCEL_DEADLINE_HOURS", 3)
        if lesson.start_time - timezone.now() < timedelta(hours=cancel_deadline):
            return Response(
                {
                    "error": _(
                        "Lesson can only be cancelled up to {hours} hours before start."
                    ).format(hours=cancel_deadline)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = None
        notification_recipient = None
        notification_message = ""

        if (
            user.role == BaseUser.ROLE_STUDENT
            and hasattr(user, "student_profile")
            and lesson.student == user.student_profile
        ):
            new_status = LessonStatus.CANCELLED_BY_STUDENT
            notification_recipient = lesson.teacher.user
            notification_message = _("Student {name} cancelled lesson {id}.").format(
                name=user.student_profile.first_name, id=lesson.id
            )
            logger.info(f"Lesson {lesson.id} cancelled by student {user.email}.")
        elif (
            user.role == BaseUser.ROLE_TEACHER
            and hasattr(user, "teacher_profile")
            and lesson.teacher == user.teacher_profile
        ):
            new_status = LessonStatus.CANCELLED_BY_TEACHER
            notification_recipient = lesson.student.user
            notification_message = _("Teacher {name} cancelled lesson {id}.").format(
                name=user.teacher_profile.first_name, id=lesson.id
            )
            logger.info(f"Lesson {lesson.id} cancelled by teacher {user.email}.")
        else:
            raise PermissionDenied(
                _("You do not have permission to cancel this lesson.")
            )

        lesson.status = new_status
        lesson.save(update_fields=["status"])

        if notification_recipient:
            try:
                InternalNotification.objects.create(
                    user=notification_recipient,
                    lesson=lesson,
                    message=notification_message,
                )
            except Exception as e:
                logger.error(
                    f"Failed to create cancellation notification for lesson {lesson.id}: {e}"
                )

        return Response(
            {"status": lesson.status, "message": _("Lesson cancelled successfully.")}
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
        permission_classes=[IsAuthenticated, IsTeacher],
    )
    def approve_lesson(self, request, pk=None):
        lesson = self.get_object()
        user = request.user

        if (
            not hasattr(user, "teacher_profile")
            or lesson.teacher != user.teacher_profile
        ):
            raise PermissionDenied(_("Only the teacher of this lesson can approve it."))

        if lesson.status == LessonStatus.VOID:
            lesson.status = LessonStatus.APPROVED
            lesson.save(update_fields=["status"])
            logger.info(f"Lesson {lesson.id} approved by teacher {user.email}.")
            try:
                message = _(
                    "Teacher {name} approved your lesson {id} for {time}."
                ).format(
                    name=user.teacher_profile.first_name,
                    id=lesson.id,
                    time=lesson.start_time.strftime("%Y-%m-%d %H:%M"),
                )
                InternalNotification.objects.create(
                    user=lesson.student.user, lesson=lesson, message=message
                )
            except Exception as e:
                logger.error(
                    f"Failed to create approval notification for lesson {lesson.id}: {e}"
                )

            serializer = self.get_serializer(lesson)
            return Response(serializer.data)
        else:
            return Response(
                {
                    "error": _("Lesson already has status '{status}'.").format(
                        status=lesson.get_status_display()
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True,
        methods=["post", "patch"],
        url_path="mark-paid",
        permission_classes=[IsAuthenticated, IsTeacher],
    )
    def mark_paid(self, request, pk=None):
        lesson = self.get_object()
        user = request.user
        if (
            not hasattr(user, "teacher_profile")
            or lesson.teacher != user.teacher_profile
        ):
            raise PermissionDenied(
                _("Only the teacher of this lesson can mark it as paid.")
            )

        is_paid_value = request.data.get("is_paid")
        if is_paid_value is None:
            return Response(
                {"error": _("Field 'is_paid' (boolean) is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(is_paid_value, bool):
            return Response(
                {"error": _("Field 'is_paid' must be a boolean.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lesson.is_paid = is_paid_value
        lesson.save(update_fields=["is_paid"])
        logger.info(
            f"Lesson {lesson.id} marked as {'paid' if is_paid_value else 'unpaid'} by teacher {user.email}."
        )
        return Response(
            {"is_paid": lesson.is_paid, "message": _("Lesson payment status updated.")}
        )

    @action(
        detail=True,
        methods=["patch"],
        url_path="homework",
        permission_classes=[IsAuthenticated, IsTeacher],
    )
    def add_homework(self, request, pk=None):
        lesson = self.get_object()
        user = request.user
        if (
            not hasattr(user, "teacher_profile")
            or lesson.teacher != user.teacher_profile
        ):
            raise PermissionDenied(
                _("Only the teacher of this lesson can add homework.")
            )

        serializer = self.get_serializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if set(serializer.validated_data.keys()) != {"homework"}:
            raise ValidationError(
                _("Only the 'homework' field can be updated via this endpoint.")
            )

        serializer.save()
        logger.info(f"Homework updated for lesson {lesson.id} by teacher {user.email}.")
        return Response({"homework": serializer.data.get("homework")})


class RatingViewSet(viewsets.ModelViewSet):
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Rating.objects.select_related(
            "student", "teacher", "lesson", "student__user", "teacher__user"
        )
        teacher_id = self.request.query_params.get("teacher_id")
        student_id = self.request.query_params.get("student_id")

        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        elif student_id:
            if (
                hasattr(user, "student_profile")
                and str(user.student_profile.id) == student_id
            ):
                queryset = queryset.filter(student_id=student_id)
            else:
                return Rating.objects.none()
        elif hasattr(user, "teacher_profile"):
            queryset = queryset.filter(teacher=user.teacher_profile)
        elif hasattr(user, "student_profile"):
            queryset = queryset.filter(student=user.student_profile)
        else:
            return Rating.objects.none()

        return queryset.order_by("-created_at")

    def get_permissions(self):
        action = getattr(self, "action", None)
        if action == "create":
            self.permission_classes = [IsAuthenticated, IsStudent]
        elif action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsStudent, IsProfileOwner]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, "student_profile"):
            raise PermissionDenied("Only students can leave ratings.")

        lesson = serializer.validated_data.get("lesson")
        if not lesson:
            raise ValidationError(
                {"lesson_id_write": "Lesson is required to create a rating."}
            )
        teacher = lesson.teacher
        rating = serializer.save(student=user.student_profile, teacher=teacher)
        logger.info(
            f"Rating {rating.id} created by student {user.email} for lesson {rating.lesson_id}."
        )


class InternalNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = InternalNotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return InternalNotification.objects.filter(
            user=self.request.user
        ).select_related("lesson")

    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        if set(serializer.validated_data.keys()) != {"is_read"}:
            raise ValidationError(_("Only the 'is_read' field can be updated."))
        if serializer.instance.user != self.request.user:
            raise PermissionDenied(_("You can only update your own notifications."))
        serializer.save()

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_as_read(self, request):
        count = InternalNotification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        logger.info(
            f"{count} notifications marked as read for user {request.user.email}."
        )
        return Response(
            {"message": _("{count} notifications marked as read.").format(count=count)}
        )


class MyStudentsView(generics.ListAPIView):
    serializer_class = MyStudentSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "user__email"]

    def get_queryset(self):
        teacher_profile = getattr(self.request.user, "teacher_profile", None)
        if not teacher_profile:
            return Student.objects.none()

        student_ids = (
            Lesson.objects.filter(teacher=teacher_profile)
            .values_list("student_id", flat=True)
            .distinct()
        )
        return (
            Student.objects.filter(id__in=student_ids)
            .select_related("user")
            .order_by("last_name", "first_name")
        )


class TeacherSubjectListView(generics.ListAPIView):
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs.get("teacher_id")
        teacher = get_object_or_404(
            Teacher.objects.prefetch_related("subjects"), pk=teacher_id
        )
        return teacher.subjects.all()


class TeacherAvailabilityView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def get(request, teacher_id):
        teacher = get_object_or_404(Teacher, pk=teacher_id)
        date_from_str = request.query_params.get(
            "date_from", timezone.now().date().isoformat()
        )
        date_to_str = request.query_params.get(
            "date_to", (timezone.now().date() + timedelta(days=30)).isoformat()
        )

        try:
            date_from = datetime.fromisoformat(date_from_str).date()
            date_to = datetime.fromisoformat(date_to_str).date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        schedules = Schedule.objects.filter(teacher=teacher).order_by(
            "weekday", "start_time"
        )
        booked_lessons = Lesson.objects.filter(
            teacher=teacher,
            status__in=[LessonStatus.VOID, LessonStatus.APPROVED],
            start_time__date__gte=date_from,
            start_time__date__lte=date_to,
        ).values_list("start_time", "end_time")

        booked_slots = set()
        for start, end in booked_lessons:
            if start and end:
                current = start
                while current < end:
                    booked_slots.add(current.replace(tzinfo=None))
                    current += timedelta(hours=1)
            elif start:
                booked_slots.add(start.replace(tzinfo=None))

        availability = {}
        current_date = date_from
        while current_date <= date_to:
            weekday_name = current_date.strftime("%A").lower()
            daily_slots = []
            day_schedules = schedules.filter(weekday=weekday_name)
            for schedule_slot in day_schedules:
                try:
                    slot_start_dt = timezone.make_aware(
                        datetime.combine(current_date, schedule_slot.start_time)
                    )
                    slot_end_dt = timezone.make_aware(
                        datetime.combine(current_date, schedule_slot.end_time)
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid time combine for teacher {teacher.id} on {current_date} for slot"
                        f" {schedule_slot.start_time}-{schedule_slot.end_time}"
                    )
                    continue

                current_slot_dt = slot_start_dt
                while current_slot_dt < slot_end_dt:
                    if (
                        current_slot_dt.replace(tzinfo=None) not in booked_slots
                        and current_slot_dt > timezone.now()
                    ):
                        next_slot_dt = current_slot_dt + timedelta(hours=1)
                        can_book_2_hours = False

                        if (
                            next_slot_dt < slot_end_dt
                            and next_slot_dt.replace(tzinfo=None) not in booked_slots
                        ):
                            can_book_2_hours = True

                        daily_slots.append(
                            {
                                "start_time": current_slot_dt.isoformat(),
                                "can_book_2_hours": can_book_2_hours,
                            }
                        )
                    current_slot_dt += timedelta(hours=1)

            if daily_slots:
                availability[current_date.isoformat()] = daily_slots
            current_date += timedelta(days=1)

        return Response(availability)
