import logging
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status, filters
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser

from user.models import (
    BaseUser,
    Teacher,
    Student,
    City,
    Subject,
    Language,
    CategoriesOfStudents,
)
from user.permissions import IsTeacher, IsStudent, IsProfileOwner
from user.serializers import (
    UserRegistrationSerializer,
    TeacherCabinetSerializer,
    StudentProfileSerializer,
    CitySerializer,
    SubjectSerializer,
    LanguageSerializer,
    CategoriesOfStudentsSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    TeacherRegistrationSerializer,
    ChangePasswordSerializer,
    TeacherListSerializer,
    TeacherPublicProfileSerializer,
    MyTokenObtainPairSerializer,
    ResendActivationEmailSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class CityListView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    pagination_class = None


class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class LanguageListView(generics.ListAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class CategoriesOfStudentsListView(generics.ListAPIView):
    queryset = CategoriesOfStudents.objects.all()
    serializer_class = CategoriesOfStudentsSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class TeacherListView(generics.ListAPIView):
    queryset = (
        Teacher.objects.all()
        .select_related("user", "city")
        .prefetch_related("subjects", "categories")
    )
    serializer_class = TeacherListSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "first_name",
        "last_name",
        "about_me",
        "subjects__name",
        "city__name",
        "categories__name",
    ]
    ordering_fields = [
        "lesson_price",
        "teaching_experience",
        "created_at, is_verified",
    ]
    pagination_class = None


class TeacherDetailView(generics.RetrieveAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherPublicProfileSerializer
    permission_classes = [AllowAny]
    lookup_field = "pk"


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def get(request, token):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            if payload.get("purpose") != "activation":
                raise jwt.InvalidTokenError("Invalid token purpose.")
            user_id = payload.get("user_id")
            if not user_id:
                raise jwt.InvalidTokenError("Token payload missing user_id")
            user = get_object_or_404(User, id=user_id)

            if user.is_active:
                logger.warning(
                    f"Account already active for user {user.email} (ID: {user.id})."
                )
                refresh = RefreshToken.for_user(user)
                if user.role == BaseUser.ROLE_STUDENT:
                    redirect_path = "/profile/student/me/"
                elif user.role == BaseUser.ROLE_TEACHER:
                    redirect_path = "/profile/teacher/complete/"
                else:
                    redirect_path = "/"

                return Response(
                    {
                        "message": _("Account is already activated. You can log in."),
                        "access_token": str(refresh.access_token),
                        "refresh_token": str(refresh),
                        "redirect_to": settings.FRONTEND_URL.rstrip("/")
                        + redirect_path,
                    },
                    status=status.HTTP_200_OK,
                )

            user.is_active = True
            user.save(update_fields=["is_active"])
            logger.info(
                f"Account activated successfully for {user.email} (ID: {user.id})."
            )

            if user.role == BaseUser.ROLE_STUDENT:
                try:
                    student_profile, created = Student.objects.get_or_create(user=user)
                    if created:
                        logger.info(
                            f"Student profile created for {user.email} (ID: {user.id})."
                        )
                    else:
                        logger.warning(
                            f"Student profile already existed for {user.email} (ID: {user.id})."
                        )
                    redirect_path = "/profile/student/me/"
                except Exception as e:
                    logger.error(
                        f"Error creating/retrieving student profile for {user.email} (ID: {user.id}): {e}"
                    )
                    refresh = RefreshToken.for_user(user)
                    return Response(
                        {
                            "message": _(
                                "Account activated, but there was an issue accessing/creating your student profile. "
                                "Please contact support."
                            ),
                            "access_token": str(refresh.access_token),
                            "refresh_token": str(refresh),
                            "redirect_to": settings.FRONTEND_URL.rstrip("/") + "/",
                        },
                        status=status.HTTP_200_OK,
                    )
            elif user.role == BaseUser.ROLE_TEACHER:
                redirect_path = "/profile/teacher/complete/"
            else:
                logger.error(
                    f"Unknown role '{user.role}' for user {user.email} (ID: {user.id}) during activation."
                )
                redirect_path = "/"

            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "message": _("Account activated successfully!"),
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "redirect_to": settings.FRONTEND_URL.rstrip("/") + redirect_path,
                    "role": user.role,
                },
                status=status.HTTP_200_OK,
            )

        except jwt.ExpiredSignatureError:
            logger.warning(f"Activation token expired: {token}")
            return Response(
                {"error": _("Activation link has expired.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (jwt.InvalidTokenError, jwt.DecodeError):
            logger.warning(f"Invalid activation token: {token}")
            return Response(
                {"error": _("Activation link is invalid.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except User.DoesNotExist:
            logger.error(f"User not found for activation token: {token}")
            return Response(
                {"error": _("User not found.")}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Unexpected error during account activation: {e}")
            return Response(
                {"error": _("An unexpected error occurred during activation.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CompleteTeacherProfileView(generics.CreateAPIView):
    serializer_class = TeacherRegistrationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Teacher.objects.none()
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != BaseUser.ROLE_TEACHER:
            raise PermissionDenied(
                _("Only users with the 'teacher' role can create a teacher profile.")
            )
        if hasattr(user, "teacher_profile") and user.teacher_profile is not None:
            raise ValidationError(_("Teacher profile already exists for this user."))

        serializer.save(user=user)
        logger.info(f"Teacher profile completed for user {user.email} (ID: {user.id}).")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data
        try:
            redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}{reverse('user:teacher-profile-me')}"
            response_data["redirect_to"] = redirect_url
        except Exception as e:
            logger.error(
                f"Could not reverse URL for teacher-profile-me or construct redirect: {e}"
            )
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class TeacherProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = TeacherCabinetSerializer
    permission_classes = [IsAuthenticated, IsTeacher, IsProfileOwner]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        return get_object_or_404(Teacher, user=self.request.user)


class StudentProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsStudent, IsProfileOwner]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        student_profile, created = Student.objects.get_or_create(user=self.request.user)
        if created:
            logger.warning(
                f"Student profile was missing for user {self.request.user.email} (ID: {self.request.user.id}) and was "
                f"created on demand in StudentProfileMeView."
            )
        return student_profile


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            logger.info(
                f"Password changed successfully for user {self.request.user.email} (ID: {self.request.user.id})."
            )
            return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": _(
                    "If an account with this email exists, a password reset link has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": _(
                    "Password has been reset successfully. You can now log in with your new password."
                )
            },
            status=status.HTTP_200_OK,
        )


class UserLoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = MyTokenObtainPairSerializer


class ResendActivationEmailView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def post(request, *args, **kwargs):
        serializer = ResendActivationEmailSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            try:
                activation_token = UserRegistrationSerializer.generate_activation_token(
                    user
                )
                activation_url = (
                    f"{settings.FRONTEND_URL.rstrip('/')}/activate/{activation_token}"
                )

                UserRegistrationSerializer.send_activation_email(
                    user.email, activation_url
                )

                logger.info(
                    f"Successfully resent activation email to {user.email} (ID: {user.id}) via dedicated endpoint."
                )
                return Response(
                    {
                        "detail": _(
                            "Activation email has been resent. Please check your inbox."
                        )
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                logger.error(
                    f"Failed to resend activation email for {user.email} (ID: {user.id}) via dedicated endpoint. "
                    f"Error: {e}"
                )
                return Response(
                    {
                        "detail": _(
                            "An error occurred while trying to send the activation email. Please try again later."
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
