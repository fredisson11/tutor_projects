from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from user.models import Student, Teacher, Specialty, BaseUser


class StudentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(source="user.email")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")

    class Meta:
        model = Student
        fields = ["email", "first_name", "last_name", "password", "confirm_password"]

    def validate(self, attrs):
        """Перевірка на відповідність пароля"""
        if attrs["password"] != attrs["confirm_password"]:
            raise ValidationError("Паролі не співпадають")
        return attrs

    def create(self, validated_data):
        """Створення нового студента"""
        validated_data["password"] = make_password(validated_data["password"])
        student = Student.objects.create(user=BaseUser.objects.create(**validated_data))
        student.save()
        return student


class TeacherSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(source="user.email")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    bio = serializers.CharField(source="user.bio", required=False)
    age = serializers.IntegerField(source="user.age", required=False)
    rating = serializers.FloatField(source="user.rating", required=False)
    specialty = serializers.PrimaryKeyRelatedField(queryset=Specialty.objects.all())

    class Meta:
        model = Teacher
        fields = [
            "email",
            "first_name",
            "last_name",
            "bio",
            "age",
            "rating",
            "specialty",
            "password",
            "confirm_password",
        ]

    def validate(self, attrs):
        """Перевірка на відповідність пароля"""
        if attrs["password"] != attrs["confirm_password"]:
            raise ValidationError("Паролі не співпадають")
        return attrs

    def create(self, validated_data):
        """Створення нового викладача"""
        validated_data["password"] = make_password(validated_data["password"])
        teacher = Teacher.objects.create(user=BaseUser.objects.create(**validated_data))
        teacher.save()
        return teacher


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
            raise serializers.ValidationError("Старий пароль невірний.")

        if new_password != confirm_password:
            raise serializers.ValidationError(
                "Новий пароль і підтвердження не співпадають."
            )

        if old_password == new_password:
            raise serializers.ValidationError(
                "Новий пароль не може бути таким самим, як старий."
            )
        return data
