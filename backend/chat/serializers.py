from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from typing import Any, Optional, TypedDict, cast
from .models import Message, Ticket


class _MiniUser(TypedDict, total=False):
    id: int
    email: Optional[str]


class _MetaUsage(TypedDict, total=False):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class _MetaModel(TypedDict, total=False):
    name: str
    usage: _MetaUsage


class _ResponseMeta(TypedDict, total=False):
    model: _MetaModel


def _mini_user(u: Optional[AbstractBaseUser]) -> Optional[_MiniUser]:
    if u is None:
        return None
    data: _MiniUser = {}
    user_id = getattr(u, "id", None)
    if user_id is not None:
        try:
            data["id"] = int(user_id)
        except (TypeError, ValueError):
            pass
    email = getattr(u, "email", None)
    if email is None or isinstance(email, str):
        data["email"] = email
    return data


def _safe_meta(meta: Any) -> _ResponseMeta:
    return cast(_ResponseMeta, meta if isinstance(meta, dict) else {})


# ---- Chat: Tickets ----
class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    content = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    settings = serializers.JSONField(required=False)

    def validate_subject(self, v: str):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Subject cannot be empty.")
        return v


class TicketSerializer(serializers.ModelSerializer):
    assignee = serializers.SerializerMethodField()

    def get_assignee(self, obj: Ticket) -> Optional[_MiniUser]:
        return _mini_user(getattr(obj, "assignee", None))

    class Meta:
        model = Ticket
        fields = ["id", "subject", "status", "settings", "assignee", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminTicketPatchSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Ticket.Status.choices, required=False)
    assignee_id = serializers.IntegerField(required=False)


# ---- Chat: Messages ----
class MessageCreateSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    content = serializers.CharField(allow_blank=False, max_length=4000)

    def validate_content(self, v: str):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Content cannot be empty.")
        return v


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()

    def get_sender(self, obj: Message) -> Optional[_MiniUser]:
        return _mini_user(getattr(obj, "sender", None))

    class Meta:
        model = Message
        fields = ["id", "ticket", "content", "is_ai", "response_meta", "sender", "created_at"]
        read_only_fields = ["id", "created_at", "is_ai", "response_meta"]


# ---- Chat: AI (Ollama) ----
class AIRequestSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    content = serializers.CharField(allow_blank=False, max_length=4000)


class AIResponseSerializer(serializers.Serializer):
    message_id = serializers.IntegerField()
    content = serializers.CharField()


# === File: chat/views.py ===
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from .models import Ticket, Message
from .serializers import (
    TicketCreateSerializer,
    TicketSerializer,
    AdminTicketPatchSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class TicketCollectionView(APIView):
    """GET: 列出客服單；POST: 建立客服單
    - 非管理員：僅能看到自己的 ticket
    - 管理員：可用 ?mine=true 僅看自己，預設看全部
    支援查詢：?status=open|closed
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Ticket.objects.all()
        mine = request.query_params.get("mine")
        status_q = request.query_params.get("status")

        if not request.user.is_staff or (mine and mine.lower() == "true"):
            qs = qs.filter(user=request.user)
        if status_q:
            qs = qs.filter(status=status_q)
        qs = qs.order_by("-updated_at", "-id")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        data = TicketSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        ser = TicketCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], ser.validated_data)
        subject = cast(str, validated["subject"]).strip()
        content = cast(str, validated.get("content", "") or "").strip()
        settings = validated.get("settings") or {}

        ticket = Ticket.objects.create(user=request.user, subject=subject, settings=settings)
        if content:
            Message.objects.create(ticket=ticket, content=content, is_ai=False, sender=request.user)
        return Response({"ticket_id": ticket.id}, status=status.HTTP_201_CREATED)


class MessageCollectionView(APIView):
    """GET: 讀取某 ticket 的訊息；POST: 在某 ticket 新增訊息"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        ticket_id = request.query_params.get("ticket_id")
        if not ticket_id:
            return Response({"detail": "Missing ticket_id"}, status=status.HTTP_400_BAD_REQUEST)
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if ticket.user_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Not your ticket"}, status=status.HTTP_403_FORBIDDEN)

        qs = Message.objects.filter(ticket=ticket).order_by("created_at", "id")
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        data = MessageSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        ser = MessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], ser.validated_data)
        ticket_id = int(validated["ticket_id"])
        content = cast(str, validated["content"]).strip()

        ticket = get_object_or_404(Ticket, id=ticket_id)
        if ticket.user_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Not your ticket"}, status=status.HTTP_403_FORBIDDEN)

        msg = Message.objects.create(ticket=ticket, content=content, is_ai=False, sender=request.user)
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class AdminTicketPatchView(APIView):
    """Admin：更新 ticket（狀態/指派）。
    PATCH /chat/admin/tickets/{ticket_id}  body: {status?, assignee_id?}
    """

    permission_classes = [IsAdminUser]

    def patch(self, request, ticket_id: int):
        ser = AdminTicketPatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], ser.validated_data)
        ticket = get_object_or_404(Ticket, id=ticket_id)

        changed = False
        status_val = validated.get("status")
        assignee_id = validated.get("assignee_id")

        if status_val:
            if status_val == Ticket.Status.CLOSED:
                ticket.close()
            else:
                ticket.status = status_val
                ticket.save(update_fields=["status", "updated_at"])
            changed = True

        if assignee_id is not None:
            User = get_user_model()
            assignee = get_object_or_404(User, id=assignee_id)
            ticket.assignee = assignee
            ticket.save(update_fields=["assignee", "updated_at"])
            changed = True

        if not changed:
            return Response({"detail": "No fields changed"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)
