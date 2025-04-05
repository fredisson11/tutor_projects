from rest_framework import serializers
from applications.models import TeacherApplication


class TeacherApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherApplication
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "specialty",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
