from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import get_user_model
from user.models import (
    Student,
    Teacher,
    Language,
    Country,
    City,
    Subject,
    CategoriesOfStudents,
    BaseUser,
)

import re

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=BaseUser.ROLES_CHOICES)

    class Meta:
        model = User
        fields = ["email", "password", "role"]

    @staticmethod
    def validate_email(value):
        try:
            validate_email(value)
        except Exception:
            raise serializers.ValidationError("Невірний формат email")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Користувач з таким email вже існує")
        return value

    @staticmethod
    def validate_password(value):
        if len(value) < 8:
            raise serializers.ValidationError("Пароль має містити не менше 8 символів.")
        if not re.search(r"[A-Za-z]", value):
            raise serializers.ValidationError("Пароль має містити хоча б одну літеру.")
        if not re.search(r"\d", value):
            raise serializers.ValidationError("Пароль має містити хоча б одну цифру.")
        if not re.search(r"[@$!%*?&]", value):
            raise serializers.ValidationError(
                "Пароль має містити хоча б один спеціальний символ (@, $, !, %, *, ?, &)."
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        user.role = validated_data["role"]
        user.is_active = False
        user.save()

        return user


class StudentProfileSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    language = serializers.PrimaryKeyRelatedField(queryset=Language.objects.all())

    class Meta:
        model = Student
        fields = [
            "first_name",
            "last_name",
            "age",
            "phone",
            "photo",
            "city",
            "country",
            "language",
        ]


class TeacherProfileSerializer(serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), required=False
    )
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False
    )
    categories = serializers.PrimaryKeyRelatedField(
        queryset=CategoriesOfStudents.objects.all(), many=True, required=False
    )
    subjects = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), many=True, required=False
    )

    class Meta:
        model = Teacher
        fields = [
            "first_name",
            "last_name",
            "age",
            "photo",
            "city",
            "country",
            "language",
            "categories",
            "teaching_experience",
            "about_me",
            "hobbies",
            "education",
            "lesson_flow",
            "lesson_price",
            "lesson_duration",
            "subjects",
            "telegram",
            "whatsapp",
            "viber",
            "instagram",
        ]


def validate_city_belongs_to_country(attrs):
    country = attrs.get("country")
    city = attrs.get("city")
    if city and country and city.country != country:
        raise ValidationError("Обране місто не належить вибраній країні.")
    return attrs


# -------------------- CitySerializer --------------------
class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name"]


# -------------------- ChangePasswordSerializer --------------------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        user = self.context["request"].user
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if not user.check_password(old_password):
            raise serializers.ValidationError("Old password is invalid")

        if new_password != confirm_password:
            raise serializers.ValidationError(
                "New password and confirm_password do not match"
            )

        if old_password == new_password:
            raise serializers.ValidationError(
                "New password cannot be the same as the old one."
            )
        return data
