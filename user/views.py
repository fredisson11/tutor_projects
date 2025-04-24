from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from user.models import City, Country, Language, Student, Teacher, CategoriesOfStudents
from user.serializers import StudentProfileSerializer, TeacherProfileSerializer


User = get_user_model()


class RegisterUserView(APIView):
    @staticmethod
    def post(request):
        email = request.data.get("email")
        password = request.data.get("password")
        role = request.data.get("role")

        if not email or not password or not role:
            return Response({"error": "Email, password and role are required"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "User with this email already exists."}, status=400)

        user = User.objects.create_user(email=email, password=password)
        user.role = role
        user.is_active = False
        user.save()

        # Створення активаційного токену
        token_expiry = datetime.utcnow() + timedelta(hours=24)
        activation_token = jwt.encode(
            {"user_id": user.id, "exp": token_expiry},
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        # Активаційне посилання
        activation_url = f"https://{get_current_site(request).domain}/activate/{activation_token}/"

        # Відправка email з посиланням для активації акаунта
        send_mail(
            "Activate your account",
            f"Click the link to activate your account: {activation_url}",
            "from@example.com",
            [email],
        )

        return Response({"message": "Please check your email for activation"}, status=201)


class ActivateAccountView(APIView):
    @staticmethod
    def get(request, token):
        try:
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_token["user_id"]
            user = User.objects.get(id=user_id)

            if datetime.utcnow() > datetime.utcfromtimestamp(decoded_token["exp"]):
                return Response({"error": "Activation link expired"}, status=400)

            user.is_active = True
            user.save()

            # Перевірка ролі користувача
            if user.role == "student":
                return redirect("student_profile")  # Redirect to student profile edit
            elif user.role == "teacher":
                return redirect("teacher_profile")  # Redirect to teacher profile creation
            return Response({"error": "Invalid role"}, status=400)

        except jwt.ExpiredSignatureError:
            return Response({"error": "Activation link expired"}, status=400)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=400)


class StudentProfileView(APIView):
    @staticmethod
    def post(request, user_id):
        try:
            user = User.objects.get(id=user_id)

            if user.role != "student":
                return Response({"error": "User is not a student"}, status=400)

            serializer = StudentProfileSerializer(data=request.data)

            if serializer.is_valid():
                student = (
                    user.student_profile
                    if hasattr(user, "student_profile")
                    else Student(user=user)
                )

                student.first_name = serializer.validated_data.get("first_name")
                student.last_name = serializer.validated_data.get("last_name")
                student.age = serializer.validated_data.get("age")
                student.phone = serializer.validated_data.get("phone")
                student.photo = serializer.validated_data.get("photo")
                student.city = serializer.validated_data.get("city")
                student.language = serializer.validated_data.get("language")
                student.country = serializer.validated_data.get("country")

                student.save()

                return Response(
                    {"message": "Student profile updated successfully"}, status=200
                )
            return Response(serializer.errors, status=400)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class TeacherProfileView(APIView):
    @staticmethod
    def post(request, user_id):
        try:
            user = User.objects.get(id=user_id)

            if user.role != "teacher":
                return Response({"error": "User is not a teacher"}, status=400)

            serializer = TeacherProfileSerializer(data=request.data)

            if serializer.is_valid():
                teacher = (
                    user.teacher_profile
                    if hasattr(user, "teacher_profile")
                    else Teacher(user=user)
                )

                # Оновлення профілю вчителя
                teacher.first_name = serializer.validated_data.get("first_name")
                teacher.last_name = serializer.validated_data.get("last_name")
                teacher.age = serializer.validated_data.get("age")
                teacher.photo = serializer.validated_data.get("photo")
                teacher.city = serializer.validated_data.get("city")
                teacher.categories.set(serializer.validated_data.get("categories"))
                teacher.teaching_experience = serializer.validated_data.get(
                    "teaching_experience"
                )
                teacher.about_me = serializer.validated_data.get("about_me")
                teacher.hobbies = serializer.validated_data.get("hobbies")
                teacher.education = serializer.validated_data.get("education")
                teacher.lesson_flow = serializer.validated_data.get("lesson_flow")
                teacher.lesson_price = serializer.validated_data.get("lesson_price")
                teacher.lesson_duration = serializer.validated_data.get(
                    "lesson_duration"
                )
                teacher.subjects.set(serializer.validated_data.get("subjects"))
                teacher.telegram = serializer.validated_data.get("telegram")
                teacher.whatsapp = serializer.validated_data.get("whatsapp")
                teacher.viber = serializer.validated_data.get("viber")
                teacher.instagram = serializer.validated_data.get("instagram")

                teacher.save()

                return Response(
                    {"message": "Teacher profile updated successfully"}, status=200
                )
            return Response(serializer.errors, status=400)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
