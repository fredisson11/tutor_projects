from django.db import models
from django.utils.translation import gettext_lazy as _
from user.models import Specialty


class TeacherApplication(models.Model):
    """Анкета на подачу заявки для викладача"""

    first_name = models.CharField(_("Ім'я"), max_length=50)
    last_name = models.CharField(_("Прізвище"), max_length=50)
    email = models.EmailField(_("Email"))
    specialty = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, null=True, verbose_name=_("Спеціальність")
    )
    comment = models.TextField(_("Коментар"), blank=True)
    created_at = models.DateTimeField(_("Дата подання"), auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.email}"
