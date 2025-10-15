# auth_app/serializers.py
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import serializers

UserModel = get_user_model()

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    display_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_email(self, value):
        if UserModel.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email 已被使用")
        return value

    def create(self, validated_data):
        email = (validated_data["email"] or "").strip()
        password = validated_data["password"]
        display_name = validated_data.get("display_name") or ""

        # 預先建立暫時 user 物件給密碼驗證使用
        temp_user = UserModel(email=email)
        if hasattr(temp_user, "display_name"):
            temp_user.display_name = display_name

        try:
            validate_password(password, user=temp_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        # 建立使用者（相容不同 User 模型）
        user_kwargs = {}
        if any(getattr(f, "name", None) == "username" for f in UserModel._meta.get_fields()):
            user_kwargs["username"] = email  # 以 email 當 username 以簡化
        if hasattr(UserModel, "display_name"):
            user_kwargs["display_name"] = display_name

        try:
            user = UserModel.objects.create_user(
                email=email,
                password=password,
                **user_kwargs,
            )
        except IntegrityError:
            raise serializers.ValidationError({"email": "Email 已被使用"})

        return user


class MeSerializer(serializers.Serializer):
    # 為了相容不同欄位設計，動態輸出
    def to_representation(self, instance):
        return {
            "id": getattr(instance, "id", None),
            "email": getattr(instance, "email", None),
            "display_name": getattr(instance, "display_name", None),
            "role": getattr(instance, "role", None),
            "is_active": getattr(instance, "is_active", True),
        }
