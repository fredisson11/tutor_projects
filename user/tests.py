from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core import mail

from user.serializers import User


def test_user_registration_sends_email(self):
    url = reverse("user:register_user")
    data = {
        "email": "testemail@example.com",
        "password": "strongpass123",
        "role": "teacher",
    }
    response = self.client.post(url, data, format="json")
    self.assertEqual(len(mail.outbox), 1)
    self.assertIn("Activate your account", mail.outbox[0].subject)


class UserRegistrationTest(APITestCase):
    def test_user_registration(self):
        url = reverse("user:register_user")
        data = {
            "email": "te    stuser@example.com",
            "password": "pass",
            "role": "student",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertEqual(
            response.data["message"], "Please check your email for activation"
        )

        # Додаткові перевірки:
        user = User.objects.get(email="testuser@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.role, "student")