# chat/urls.py
from django.urls import path
from .views import (
    TicketCollectionView, MessageCollectionView, AdminTicketPatchView,
    AIReplyView, sse_ai_reply, AssistView,
)

urlpatterns = [
    path("tickets/", TicketCollectionView.as_view(), name="chat-tickets"),
    path("messages/", MessageCollectionView.as_view(), name="chat-messages"),
    path(
        "admin/tickets/<int:ticket_id>/",
        AdminTicketPatchView.as_view(),
        name="chat-admin-ticket-patch",
    ),
    path("ai/reply/", AIReplyView.as_view(), name="chat-ai-reply"),
    path("ai/stream/", sse_ai_reply, name="chat-ai-stream"),
    path("ai/assist", AssistView.as_view(), name="chat-ai-assist"),  # 依你views的docstring是 /chat/ai/assist
]
