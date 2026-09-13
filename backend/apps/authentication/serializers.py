"""
Serializers for LifePilot User Authentication & Management.

Handles data validation and transformation for user registration, authentication (login),
user profile display/updates, and organization details.
"""

from django.contrib.auth import authenticate
from rest_framework import serializers
from apps.authentication.models import Organization, User, UserRole


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for organization workspace information."""

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "description", "is_active", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing and updating primary user profile data.
    """

    organization = OrganizationSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "organization",
            "avatar_url",
            "phone_number",
            "is_mfa_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "organization",
            "is_mfa_enabled",
            "created_at",
            "updated_at",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration. Handles email validation, password hashing,
    and optional organization association.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        min_length=8,
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    organization_name = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Optional name to create a new organization for this user.",
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "organization_name",
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        org_name = validated_data.pop("organization_name", None)
        organization = None

        if org_name:
            slug = org_name.lower().replace(" ", "-")
            organization, _ = Organization.objects.get_or_create(
                name=org_name,
                defaults={"slug": slug},
            )

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=UserRole.ADMIN if organization else UserRole.OPERATOR,
            organization=organization,
        )
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for email-based user authentication.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password")

        if email and password:
            user = authenticate(
                request=self.context.get("request"),
                username=email,
                password=password,
            )
            if not user:
                raise serializers.ValidationError(
                    "Unable to log in with provided credentials.",
                    code="authorization_failed",
                )
            if not user.is_active:
                raise serializers.ValidationError(
                    "User account is inactive or disabled.",
                    code="account_disabled",
                )
        else:
            raise serializers.ValidationError(
                "Must include 'email' and 'password'.",
                code="missing_credentials",
            )

        attrs["user"] = user
        return attrs