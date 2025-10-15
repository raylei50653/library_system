# chat/views.py
from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, TypedDict, cast

from django.contrib.auth import get_user_model
from django.http import StreamingHttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404

from rest_framework import status, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ticket, Message

# ---- 提示詞與進階助理 ----
from .services.prompting import build_messages
from .services.agent import assistant_reply

# ---- Ollama client（依你的實際路徑）----
from .services.ollama_client import chat_once, chat_stream

# ---- AI 請求/回應序列化器沿用你現有的 serializers.py ----
from .serializers import AIRequestSerializer, AIResponseSerializer


class TicketCreateRequired(TypedDict):
    subject: str


class TicketCreateOptional(TypedDict, total=False):
    content: str
    config: Dict[str, Any]


class TicketCreateData(TicketCreateRequired, TicketCreateOptional):
    pass


class MessageCreateData(TypedDict):
    ticket_id: int
    content: str


class AdminTicketPatchData(TypedDict, total=False):
    status: str
    assignee_id: int


class AIRequestData(TypedDict):
    ticket_id: int
    content: str


# ==========================
# 序列化器（這幾個就地定義，避免破壞你原有 serializers）
# ==========================

class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    content = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    # 與 README/modules.md 一致：欄位名為 config
    config = serializers.JSONField(required=False)

    def validate_subject(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Subject cannot be empty.")
        return value


class TicketOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["id", "subject", "status", "config", "assignee", "created_at", "updated_at"]


class AdminTicketPatchSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Ticket.Status.choices, required=False)
    assignee_id = serializers.IntegerField(required=False)


class MessageCreateSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    content = serializers.CharField(allow_blank=False, max_length=4000)

    def validate_content(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Content cannot be empty.")
        return value


class MessageOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "ticket", "content", "is_ai", "response_meta", "created_at"]


# ==========================
# 分頁
# ==========================

class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ==========================
# 工單 / 訊息
# ==========================

class TicketCollectionView(APIView):
    """GET: 列出客服單；POST: 建立客服單"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Ticket.objects.all().select_related("assignee")
        mine = request.query_params.get("mine")
        status_q = request.query_params.get("status")

        # 一般使用者預設只看自己的；管理員若未指定 mine=true 則可看全部
        if not request.user.is_staff or (mine and mine.lower() == "true"):
            qs = qs.filter(user=request.user)

        if status_q:
            qs = qs.filter(status=status_q)

        qs = qs.order_by("-updated_at", "-id")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        data = TicketOutSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        ser = TicketCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(TicketCreateData, ser.validated_data)
        subject = data["subject"]
        content = data.get("content", "").strip()
        config = cast(Dict[str, Any], data.get("config") or {})

        ticket: Ticket = Ticket.objects.create(user=request.user, subject=subject, config=config)
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

        ticket: Ticket = cast(Ticket, get_object_or_404(Ticket, id=ticket_id))
        if ticket.user_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Not your ticket"}, status=status.HTTP_403_FORBIDDEN)

        qs = Message.objects.filter(ticket=ticket).select_related("sender").order_by("created_at", "id")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        data = MessageOutSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        ser = MessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(MessageCreateData, ser.validated_data)
        ticket_id = data["ticket_id"]
        content = data["content"]

        ticket: Ticket = cast(Ticket, get_object_or_404(Ticket, id=ticket_id))
        if ticket.user_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Not your ticket"}, status=status.HTTP_403_FORBIDDEN)
        if ticket.status == Ticket.Status.CLOSED and not request.user.is_staff:
            return Response({"detail": "Ticket is closed."}, status=status.HTTP_400_BAD_REQUEST)

        msg: Message = Message.objects.create(ticket=ticket, content=content, is_ai=False, sender=request.user)
        return Response(MessageOutSerializer(msg).data, status=status.HTTP_201_CREATED)


class AdminTicketPatchView(APIView):
    """Admin：更新 ticket（狀態/指派）"""
    permission_classes = [IsAdminUser]

    def patch(self, request, ticket_id: int):
        ser = AdminTicketPatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = cast(AdminTicketPatchData, ser.validated_data)
        ticket: Ticket = cast(Ticket, get_object_or_404(Ticket, id=ticket_id))

        changed = False
        status_val = data.get("status")
        assignee_id = data.get("assignee_id")

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
            if not assignee.is_staff:
                return Response({"detail": "Assignee must be staff."}, status=status.HTTP_400_BAD_REQUEST)
            ticket.assignee = assignee
            ticket.save(update_fields=["assignee", "updated_at"])
            changed = True

        if not changed:
            return Response({"detail": "No fields changed"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TicketOutSerializer(ticket).data, status=status.HTTP_200_OK)


# ==========================
# AI（同步 / 串流 / 進階助理）
# ==========================

class AIReplyView(APIView):
    """同步 AI 回覆：POST /chat/ai/reply/  body: {ticket_id, content}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = AIRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = cast(AIRequestData, ser.validated_data)
        ticket_id = payload["ticket_id"]
        user_text = payload["content"].strip()

        ticket: Ticket = cast(Ticket, get_object_or_404(Ticket, id=ticket_id))
        if ticket.user_id != request.user.id and not request.user.is_staff:
            return HttpResponseForbidden("Not your ticket")

        # 取最近 16 則歷史
        history_qs = list(Message.objects.filter(ticket=ticket).order_by("-created_at")[:16])
        history = [
            {"role": ("assistant" if m.is_ai else "user"), "content": m.content}
            for m in reversed(history_qs)
        ]

        ticket_config = cast(Dict[str, Any], ticket.config or {})
        msgs = build_messages(history, user_text, ticket_settings=ticket_config)

        Message.objects.create(ticket=ticket, content=user_text, is_ai=False, sender=request.user)

        t0 = perf_counter()
        try:
            ai_text = chat_once(msgs)
        except RuntimeError as exc:
            error_msg = str(exc).strip() or "AI 模型目前不可用，請稍後再試。"
            return Response({"detail": error_msg}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        latency = perf_counter() - t0

        ai_msg: Message = Message.objects.create(
            ticket=ticket,
            content=ai_text,
            is_ai=True,
            response_meta={"model": "ollama", "latency_sec": round(latency, 3)},
        )

        out = AIResponseSerializer({"message_id": ai_msg.id, "content": ai_text}).data
        return Response(out, status=status.HTTP_200_OK)


def sse_ai_reply(request):
    """SSE 串流：GET /chat/ai/stream/?ticket_id=&content=
    前端請使用 EventSource 並逐行讀取 "data: ..."。
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Auth required")

    try:
        ticket_id = int(request.GET.get("ticket_id", "0"))
    except ValueError:
        return HttpResponseForbidden("Bad ticket_id")

    content = (request.GET.get("content") or "").strip()
    ticket: Ticket = cast(Ticket, get_object_or_404(Ticket, id=ticket_id))
    if ticket.user_id != request.user.id and not request.user.is_staff:
        return HttpResponseForbidden("Not your ticket")

    history_qs = list(Message.objects.filter(ticket=ticket).order_by("-created_at")[:16])
    history = [
        {"role": ("assistant" if m.is_ai else "user"), "content": m.content}
        for m in reversed(history_qs)
    ]
    ticket_config = cast(Dict[str, Any], ticket.config or {})
    msgs = build_messages(history, content, ticket_settings=ticket_config)

    _user_msg = Message.objects.create(ticket=ticket, content=content, is_ai=False, sender=request.user)

    def stream():
        # 起始訊號（注意必須以空行結尾，SSE 事件邊界）
        yield "data: 【系統】開始生成\n\n".encode("utf-8")
        chunks: List[str] = []
        try:
            for ch in chat_stream(msgs):
                chunks.append(ch)
                yield f"data: {ch}\n\n".encode("utf-8")
        except RuntimeError as exc:
            error_msg = str(exc).strip() or "AI 模型目前不可用，請稍後再試。"
            Message.objects.create(
                ticket=ticket,
                content=error_msg,
                is_ai=True,
                response_meta={"model": "ollama", "error": True},
            )
            yield f"data: 【系統】{error_msg}\n\n".encode("utf-8")
            yield "data: [DONE]\n\n".encode("utf-8")
            return

        Message.objects.create(
            ticket=ticket,
            content="".join(chunks),
            is_ai=True,
            response_meta={"model": "ollama", "streamed": True},
        )
        yield "data: [DONE]\n\n".encode("utf-8")

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"  # 若走 Nginx，避免緩衝
    return resp


class AssistView(APIView):
    """進階助理（RAG + 工具）：POST /chat/ai/assist  body: {ticket_id, content, use_rag?, enable_tools?}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = AIRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = cast(AIRequestData, ser.validated_data)
        ticket_id = payload["ticket_id"]
        user_text = payload["content"].strip()

        use_rag = bool(request.data.get("use_rag", True))
        enable_tools = bool(request.data.get("enable_tools", True))

        ticket: Ticket = cast(Ticket, get_object_or_404(Ticket, id=ticket_id))
        if ticket.user_id != request.user.id and not request.user.is_staff:
            return HttpResponseForbidden("Not your ticket")

        final_text, meta = assistant_reply(
            ticket=ticket,
            user_text=user_text,
            use_rag=use_rag,
            enable_tools=enable_tools,
            user=request.user,
        )

        Message.objects.create(ticket=ticket, content=user_text, is_ai=False, sender=request.user)
        ai_msg: Message = Message.objects.create(
            ticket=ticket,
            content=final_text,
            is_ai=True,
            response_meta=meta,
        )

        return Response(
            {"message_id": ai_msg.id, "content": final_text, "meta": meta},
            status=status.HTTP_200_OK,
        )
