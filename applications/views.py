from rest_framework import generics
from .models import TeacherApplication
from .serializers import TeacherApplicationSerializer


class TeacherApplicationCreateView(generics.CreateAPIView):
    queryset = TeacherApplication.objects.all()
    serializer_class = TeacherApplicationSerializer
