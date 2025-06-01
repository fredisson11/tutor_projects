import base64
import logging
import re
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db.models import Avg
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token

from user.models import (
    Student,
    Teacher,
    Language,
    City,
    Subject,
    CategoriesOfStudents,
    BaseUser,
)

try:
    from teaching.models import Schedule, Rating
    from teaching.serializers import ScheduleSerializer, PublicRatingSerializer
except ImportError:
    Schedule = None
    Rating = None

    class ScheduleSerializer(serializers.Serializer):
        pass

    class PublicRatingSerializer(serializers.Serializer):
        pass


User = get_user_model()
logger = logging.getLogger(__name__)


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name"]


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "name"]


class CategoriesOfStudentsSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source="get_name_display", read_only=True)

    class Meta:
        model = CategoriesOfStudents
        fields = ["id", "name", "name_display"]


class Base64ImageField(serializers.Field):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            try:
                format_part, imgstr = data.split(";base64,")
                ext = format_part.split("/")[-1].lower()
                if ext not in ["jpg", "jpeg", "png", "gif"]:
                    raise serializers.ValidationError(_("Unsupported image format."))
                decoded_file = base64.b64decode(imgstr)
                max_size_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 5)
                if len(decoded_file) > max_size_mb * 1024 * 1024:
                    raise serializers.ValidationError(
                        _("Image size cannot exceed {max_size}MB.").format(
                            max_size=max_size_mb
                        )
                    )
                return {"photo": decoded_file, "photo_format": ext.upper()}
            except Exception as e:
                raise serializers.ValidationError(
                    _("Error processing image: {error}").format(error=str(e))
                )
        elif data is None:
            return None
        if data:
            raise serializers.ValidationError(
                _("Invalid image format. Expected base64 string or null.")
            )
        return None

    def to_representation(self, obj):
        target_obj = None
        if isinstance(obj, BaseUser):
            if hasattr(obj, "teacher_profile") and obj.teacher_profile:
                target_obj = obj.teacher_profile
            elif hasattr(obj, "student_profile") and obj.student_profile:
                target_obj = obj.student_profile
        elif isinstance(obj, (Teacher, Student)):
            target_obj = obj

        if (
            target_obj
            and hasattr(target_obj, "photo")
            and target_obj.photo
            and hasattr(target_obj, "photo_format")
            and target_obj.photo_format
        ):
            photo_data = target_obj.photo
            if isinstance(photo_data, memoryview):
                photo_data = photo_data.tobytes()
            if isinstance(photo_data, bytes):
                encoded = base64.b64encode(photo_data).decode()
                return f"data:image/{target_obj.photo_format.lower()};base64,{encoded}"

        placeholder_url = "https://placehold.co/150x150/E0E0E0/BDBDBD?text=No+Photo"
        return placeholder_url


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    role = serializers.ChoiceField(choices=BaseUser.ROLES_CHOICES)

    class Meta:
        model = User
        fields = ["id", "email", "password", "role"]
        read_only_fields = ["id"]

    @staticmethod
    def validate_email(value):
        try:
            validate_email(value)
        except Exception:
            raise serializers.ValidationError(_("Invalid email format"))
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("User with this email already exists"))
        return value

    @staticmethod
    def validate_password(value):
        if len(value) < 8:
            raise serializers.ValidationError(
                _("Password must be at least 8 characters long.")
            )
        if not re.search(r"[A-Za-z]", value):
            raise serializers.ValidationError(
                _("Password must contain at least one letter.")
            )
        if not re.search(r"\d", value):
            raise serializers.ValidationError(
                _("Password must contain at least one digit.")
            )
        if not re.search(r"[@$.!%*?&^#()_+=-]", value):
            raise serializers.ValidationError(
                _("Password must contain at least one special character.")
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=validated_data["role"],
            is_active=False,
        )
        try:
            activation_token = self.generate_activation_token(user)
            activation_url = (
                f"{settings.FRONTEND_URL.rstrip('/')}/activate/{activation_token}"
            )
            self.send_activation_email(user.email, activation_url)
        except Exception as e:
            logger.error(
                f"Failed to send activation email for {user.email}. "
                f"Error: {e}. Deleting partially created user to allow re-registration."
            )
            user.delete()
            raise serializers.ValidationError(
                _(
                    "We encountered an issue setting up your "
                    "account: the activation email could not be sent. "
                    "Please try registering again. If the problem persists, "
                    "please contact support."
                ),
                code="activation_email_failed",
            )
        return user

    @staticmethod
    def generate_activation_token(user):
        payload = {
            "user_id": user.id,
            "purpose": "activation",
            "exp": datetime.utcnow()
            + timedelta(hours=getattr(settings, "ACTIVATION_TOKEN_LIFETIME_HOURS", 24)),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    @staticmethod
    def send_activation_email(email, activation_url):
        subject = _("Account Activation for Astra +")
        message = _(
            f"Please click the link below to activate your account:\n\n{activation_url}\n\nIf you didn't request "
            f"this, please ignore this email."
        )
        send_mail(
            subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False
        )


class TeacherRegistrationSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=True
    )
    languages = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), many=True, required=True
    )
    categories = serializers.PrimaryKeyRelatedField(
        queryset=CategoriesOfStudents.objects.all(), required=True
    )
    subjects = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), many=True, required=True
    )
    photo = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Teacher
        fields = [
            "first_name",
            "last_name",
            "age",
            "phone",
            "photo",
            "city",
            "languages",
            "categories",
            "subjects",
            "teaching_experience",
            "about_me",
            "hobbies",
            "education",
            "lesson_flow",
            "lesson_price",
            "telegram",
            "whatsapp",
            "viber",
            "instagram",
        ]

    @staticmethod
    def _validate_m2m_count(value, field_name_singular):
        if not value:
            raise serializers.ValidationError(
                _("Please select at least one {field}.").format(
                    field=_(field_name_singular)
                )
            )
        return value

    def validate_subjects(self, value):
        return self._validate_m2m_count(value, "subject")

    def validate_categories(self, value):
        return self._validate_m2m_count(value, "category")

    def validate_languages(self, value):
        return self._validate_m2m_count(value, "language")

    def create(self, validated_data):
        languages_data = validated_data.pop("languages", [])
        categories_data = validated_data.pop("categories", [])
        subjects_data = validated_data.pop("subjects", [])
        photo_internal_data = validated_data.pop("photo", None)

        teacher = Teacher.objects.create(**validated_data)

        if languages_data:
            teacher.languages.set(languages_data)
        if categories_data:
            teacher.categories.set(categories_data)
        if subjects_data:
            teacher.subjects.set(subjects_data)

        if photo_internal_data:
            teacher.photo = photo_internal_data["photo"]
            teacher.photo_format = photo_internal_data["photo_format"]
            teacher.save(update_fields=["photo", "photo_format"])

        return teacher


class StudentProfileSerializer(serializers.ModelSerializer):
    photo = Base64ImageField(required=False, allow_null=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta:
        model = Student
        fields = ["id", "first_name", "last_name", "phone", "photo", "email"]
        read_only_fields = ("id", "email")

    def update(self, instance, validated_data):
        photo_internal_data = validated_data.pop("photo", Ellipsis)

        instance = super().update(instance, validated_data)

        if photo_internal_data is None:
            if instance.photo is not None:
                instance.photo = None
                instance.photo_format = None
                instance.save(update_fields=["photo", "photo_format"])
        elif photo_internal_data is not Ellipsis:
            instance.photo = photo_internal_data["photo"]
            instance.photo_format = photo_internal_data["photo_format"]
            instance.save(update_fields=["photo", "photo_format"])

        return instance


class TeacherCabinetSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    created_at = serializers.DateTimeField(source="user.created_at", read_only=True)

    schedule = ScheduleSerializer(source="schedules", many=True, read_only=True)
    rating_summary = serializers.SerializerMethodField(read_only=True)

    languages_read = LanguageSerializer(source="languages", many=True, read_only=True)
    city_read = CitySerializer(source="city", read_only=True)
    categories_read = CategoriesOfStudentsSerializer(
        source="categories", many=True, read_only=True
    )
    subjects_read = SubjectSerializer(source="subjects", many=True, read_only=True)

    photo = Base64ImageField(required=False, allow_null=True)

    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
    )
    languages = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(),
        many=True,
        required=False,
    )
    categories = serializers.PrimaryKeyRelatedField(
        queryset=CategoriesOfStudents.objects.all(), required=False
    )
    subjects = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), many=True, required=False
    )

    class Meta:
        model = Teacher
        fields = [
            "id",
            "email",
            "role",
            "first_name",
            "last_name",
            "age",
            "phone",
            "photo",
            "city",
            "city_read",
            "languages",
            "languages_read",
            "categories",
            "categories_read",
            "subjects",
            "subjects_read",
            "teaching_experience",
            "about_me",
            "hobbies",
            "education",
            "lesson_flow",
            "lesson_price",
            "telegram",
            "whatsapp",
            "viber",
            "instagram",
            "is_verified",
            "created_at",
            "schedule",
            "rating_summary",
        ]
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_verified",
            "created_at",
            "schedule",
            "rating_summary",
            "city_read",
            "languages_read",
            "categories_read",
            "subjects_read",
        )

    @staticmethod
    def get_rating_summary(obj):
        if Rating and hasattr(obj, "ratings"):
            ratings = obj.ratings.all()
            count = ratings.count()
            average = ratings.aggregate(Avg("rating"))["rating__avg"]
            return {
                "average": round(average, 2) if average is not None else 0.0,
                "count": count,
            }
        return {"average": 0.0, "count": 0}

    @staticmethod
    def _validate_m2m_count_update(value, field_name_singular):
        if value is not None and not value:
            raise serializers.ValidationError(
                _(
                    "Please select at least one {field} or omit the field to keep current selection."
                ).format(field=_(field_name_singular))
            )
        return value

    def validate_subjects(self, value):
        return self._validate_m2m_count_update(value, "subject")

    def validate_categories(self, value):
        return self._validate_m2m_count_update(value, "category")

    def validate_languages(self, value):
        return self._validate_m2m_count_update(value, "language")

    def update(self, instance, validated_data):
        languages_data = validated_data.pop("languages", None)
        categories_data = validated_data.pop("categories", None)
        subjects_data = validated_data.pop("subjects", None)
        photo_internal_data = validated_data.pop("photo", Ellipsis)

        instance = super().update(instance, validated_data)

        needs_save_for_photo = False
        if photo_internal_data is None:
            if instance.photo is not None:
                instance.photo = None
                instance.photo_format = None
                needs_save_for_photo = True
        elif photo_internal_data is not Ellipsis:
            instance.photo = photo_internal_data["photo"]
            instance.photo_format = photo_internal_data["photo_format"]
            needs_save_for_photo = True

        if needs_save_for_photo:
            instance.save(update_fields=["photo", "photo_format"])

        if languages_data is not None:
            instance.languages.set(languages_data)
        if categories_data is not None:
            instance.categories.set(categories_data)
        if subjects_data is not None:
            instance.subjects.set(subjects_data)

        return instance


class TeacherPublicProfileSerializer(serializers.ModelSerializer):
    city = serializers.StringRelatedField(read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    categories = CategoriesOfStudentsSerializer(many=True, read_only=True)
    subjects = SubjectSerializer(many=True, read_only=True)
    photo = Base64ImageField(read_only=True)
    schedule = ScheduleSerializer(source="schedules", many=True, read_only=True)
    rating_summary = serializers.SerializerMethodField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    phone = serializers.SerializerMethodField()
    social_links_presence = serializers.SerializerMethodField()
    reviews = PublicRatingSerializer(source="ratings", many=True, read_only=True)

    class Meta:
        model = Teacher
        fields = [
            "id",
            "first_name",
            "last_name",
            "age",
            "photo",
            "city",
            "languages",
            "categories",
            "subjects",
            "teaching_experience",
            "about_me",
            "hobbies",
            "education",
            "lesson_flow",
            "lesson_price",
            "is_verified",
            "phone",
            "social_links_presence",
            "schedule",
            "rating_summary",
            "reviews",
        ]
        read_only_fields = fields

    @staticmethod
    def get_rating_summary(obj):
        if Rating and hasattr(obj, "ratings"):
            ratings = obj.ratings.all()
            count = ratings.count()
            average = ratings.aggregate(Avg("rating"))["rating__avg"]
            return {
                "average": round(average, 2) if average is not None else 0.0,
                "count": count,
            }
        return {"average": 0.0, "count": 0}

    def get_phone(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            return obj.phone
        return None

    @staticmethod
    def get_social_links_presence(obj):
        return {
            "telegram": bool(obj.telegram),
            "whatsapp": bool(obj.whatsapp),
            "viber": bool(obj.viber),
            "instagram": bool(obj.instagram),
        }


class TeacherListSerializer(serializers.ModelSerializer):
    city = serializers.StringRelatedField(read_only=True)
    subjects = SubjectSerializer(many=True, read_only=True)
    rating_summary = serializers.SerializerMethodField(read_only=True)
    photo = Base64ImageField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    categories = CategoriesOfStudentsSerializer(many=True, read_only=True)
    about_me = serializers.CharField(
        read_only=True, help_text="Short bio or first few lines of about_me"
    )

    class Meta:
        model = Teacher
        fields = [
            "id",
            "first_name",
            "last_name",
            "photo",
            "city",
            "subjects",
            "teaching_experience",
            "lesson_price",
            "rating_summary",
            "is_verified",
            "age",
            "categories",
            "about_me",
        ]

    @staticmethod
    def get_rating_summary(obj):
        if Rating and hasattr(obj, "ratings"):
            ratings = obj.ratings.all()
            count = ratings.count()
            average = ratings.aggregate(Avg("rating"))["rating__avg"]
            return {
                "average": round(average, 2) if average is not None else 0.0,
                "count": count,
            }
        return {"average": 0.0, "count": 0}


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )

    def validate(self, data):
        user = self.context["request"].user
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not user.check_password(old_password):
            raise serializers.ValidationError(
                {"old_password": _("Old password is invalid")}
            )
        if old_password == new_password:
            raise serializers.ValidationError(
                {
                    "new_password": _(
                        "New password cannot be the same as the old password."
                    )
                }
            )

        try:
            UserRegistrationSerializer.validate_password(new_password)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"new_password": e.detail})
        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = User.objects.get(email__iexact=value.lower(), is_active=True)
            self.context["user"] = user
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _(
                    "If an account with this email exists and is active, a password reset link has been sent."
                )
            )
        return value

    def save(self):
        user = self.context.get("user")
        if not user:
            logger.error(
                "PasswordResetSerializer.save() called without 'user' in context."
            )
            return

        payload = {
            "user_id": user.id,
            "purpose": "password_reset",
            "exp": datetime.utcnow()
            + timedelta(
                hours=getattr(settings, "PASSWORD_RESET_TOKEN_LIFETIME_HOURS", 1)
            ),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        reset_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/password-reset/confirm/{token}"
        )

        subject = _("Password Reset Request for Tutor Project")
        message = _(
            f"You requested a password reset for your account.\n"
            f"\nPlease click the link below to set a new password:\n{reset_url}\n\n"
            f"If you did not request this, please ignore this email.\nThis link will expire in "
            f"{getattr(settings, 'PASSWORD_RESET_TOKEN_LIFETIME_HOURS', 1)} hour(s)."
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Error sending password reset email to {user.email}: {e}")
            raise serializers.ValidationError(
                _(
                    "We encountered an issue sending the password reset email."
                    "Please try again. If the problem persists, "
                    "please contact support."
                ),
                code="password_reset_email_failed",
            )


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )
    new_password_confirm = serializers.CharField(
        required=True, style={"input_type": "password"}
    )

    def validate(self, data):
        new_password = data.get("new_password")
        new_password_confirm = data.get("new_password_confirm")
        token = data.get("token")

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": _("Passwords do not match.")}
            )

        try:
            UserRegistrationSerializer.validate_password(new_password)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"new_password": e.detail})

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            if payload.get("purpose") != "password_reset":
                raise jwt.InvalidTokenError(_("Invalid token purpose."))

            user_id = payload.get("user_id")
            if not user_id:
                raise jwt.InvalidTokenError(_("Token payload missing user_id."))

            user = User.objects.get(id=user_id, is_active=True)
            self.context["user"] = user
        except jwt.ExpiredSignatureError:
            raise serializers.ValidationError(
                {"token": _("Password reset link has expired.")}
            )
        except (jwt.InvalidTokenError, jwt.DecodeError):
            raise serializers.ValidationError(
                {"token": _("Password reset link is invalid.")}
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "token": _(
                        "User associated with this token not found or is inactive."
                    )
                }
            )

        return data

    def save(self):
        user = self.context["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        logger.info(f"Password successfully reset for user {user.email}")
        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: BaseUser) -> Token:
        token = super().get_token(user)

        token["email"] = user.email
        token["role"] = user.role

        first_name = None
        last_name = None

        if user.role == BaseUser.ROLE_TEACHER:
            if hasattr(user, "teacher_profile") and user.teacher_profile:
                first_name = user.teacher_profile.first_name
                last_name = user.teacher_profile.last_name
        elif user.role == BaseUser.ROLE_STUDENT:
            if hasattr(user, "student_profile") and user.student_profile:
                first_name = user.student_profile.first_name
                last_name = user.student_profile.last_name
        
        if first_name:
            token["first_name"] = first_name
        if last_name:
            token["last_name"] = last_name
        
        return token
