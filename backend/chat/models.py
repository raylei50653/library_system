from __future__ import annotations
from typing import Any, Dict, Optional
from django.db import models
from django.conf import settings
class PromptTemplate(models.Model):
    """可由 Admin 管理的系統提示詞模板。支援版本與啟用開關。"""
    key = models.CharField(max_length=100, unique=True)
    text = models.TextField()
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["key", "is_active"])]
        ordering = ["-updated_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.key}@v{self.version}{' (active)' if self.is_active else ''}"


class Ticket(models.Model):
    """客服單（使用者提問／問題追蹤）。"""

    id: int
    user_id: int
    assignee_id: Optional[int]
    config: Dict[str, Any]

    class Status(models.TextChoices):
        OPEN = "open", "open"
        CLOSED = "closed", "closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets"
    )
    subject = models.CharField(max_length=200)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    config = models.JSONField(default=dict, blank=True)
    assignee = models.ForeignKey(  # 可選：指派給管理員
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"#{self.id} {self.subject}"

    def close(self):
        from django.utils import timezone
        self.status = Ticket.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=["status", "closed_at", "updated_at"])


class Message(models.Model):
    """客服訊息。AI 與人類訊息通用一張表，用 is_ai 區分。"""

    id: int
    ticket_id: int
    sender_id: Optional[int]
    response_meta: Dict[str, Any]

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(  # 使用者或管理員；AI 訊息可為空
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    content = models.TextField()
    is_ai = models.BooleanField(default=False)
    response_meta = models.JSONField(default=dict, blank=True)  # model, latency, tokens, streamed
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["ticket", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        who = "AI" if self.is_ai else (self.sender_id or "user?")
        return f"[{self.ticket_id}] {who}: {self.content[:20]}" 

# --- RAG：知識庫（簡易 JSON 向量；之後可升級 pgvector） ---
class KnowledgeDoc(models.Model):
    title = models.CharField(max_length=200)
    source = models.CharField(max_length=200, blank=True, default="")  # 例如: handbook.md
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.title


class KnowledgeChunk(models.Model):
    doc = models.ForeignKey(KnowledgeDoc, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    vec = models.JSONField(default=list, blank=True)  # 存 float list；小型專案足夠
    order = models.PositiveIntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["doc", "order"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"chunk#{self.id} of {self.doc_id}"
