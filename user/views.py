from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, update_session_auth_hash
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated

from tutor_projects.settings import EMAIL_HOST_USER
from user.models import Student, Teacher
from user.serializers import (
    StudentSerializer,
    TeacherSerializer,
    ChangePasswordSerializer,
)


class BaseRegisterAPIView(APIView):
    """Базовий клас для реєстрації користувачів"""

    def register_user(self, serializer, request):
        """Загальний метод для реєстрації користувачів"""
        if serializer.is_valid():
            try:
                user = serializer.save()
                self.send_activation_email(request, user)
                return Response(
                    {"message": "Перевірте вашу пошту для підтвердження акаунту"},
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def send_activation_email(request, user):
        """Відправляє email для підтвердження акаунту"""
        try:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            activation_link = (
                f"{request.build_absolute_uri('/api/activate/')}{uid}/{token}/"
            )
            subject = "Підтвердіть ваш акаунт"
            message = render_to_string(
                "registration/email_confirmation.html",
                {"activation_link": activation_link},
            )
            send_mail(subject, message, EMAIL_HOST_USER, [user.email])
        except Exception as e:
            raise Exception(f"Не вдалося надіслати email: {str(e)}")


class RegisterStudentAPIView(BaseRegisterAPIView):
    """API для реєстрації студента"""

    def post(self, request):
        serializer = StudentSerializer(data=request.data)
        return self.register_user(serializer, request)


class RegisterTeacherAPIView(BaseRegisterAPIView):
    """API для реєстрації викладача"""

    def post(self, request):
        serializer = TeacherSerializer(data=request.data)
        return self.register_user(serializer, request)


class ActivateAccountAPIView(APIView):
    """API для активації акаунту через email"""

    @staticmethod
    def get(request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = (
                Student.objects.filter(pk=uid).first()
                or Teacher.objects.filter(pk=uid).first()
            )
        except (TypeError, ValueError, OverflowError):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response(
                {"message": "Акаунт активовано, тепер ви можете увійти"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Недійсний або застарілий токен"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginAPIView(APIView):
    """API для авторизації"""

    @staticmethod
    def post(request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(email=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response(
                {"refresh": str(refresh), "access": str(refresh.access_token)},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Невірні облікові дані"}, status=status.HTTP_400_BAD_REQUEST
        )


class StudentMeAPIView(generics.RetrieveAPIView):
    """API для отримання інформації про поточного студента"""

    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.student_profile


class TeacherMeAPIView(generics.RetrieveAPIView):
    """API для отримання інформації про поточного викладача"""

    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.teacher_profile


class ChangePasswordAPIView(APIView):
    """В'юшка для зміни пароля для студента чи викладача"""

    @staticmethod
    def post(request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data["new_password"]
            user.set_password(new_password)
            user.save()

            update_session_auth_hash(request, user)

            return Response(
                {"message": "Пароль успішно змінено"}, status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
