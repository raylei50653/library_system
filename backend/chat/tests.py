import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import Ticket, Message
from chat.services.agent import assistant_reply

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(email="reader@example.com", password="Pass1234!")


@pytest.fixture
def other_user(db):
    User = get_user_model()
    return User.objects.create_user(email="other@example.com", password="Pass1234!")


@pytest.fixture
def staff_user(db):
    User = get_user_model()
    return User.objects.create_user(
        email="staff@example.com", password="Pass1234!", is_staff=True
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


def test_create_ticket_with_initial_message(auth_client, user):
    url = reverse("chat-tickets")
    payload = {
        "subject": "借閱問題",
        "content": "想了解續借規則",
        "config": {"priority": "normal"},
    }

    resp = auth_client.post(url, payload, format="json")

    assert resp.status_code == 201
    ticket_id = resp.json()["ticket_id"]
    ticket = Ticket.objects.get(id=ticket_id)
    assert ticket.user_id == user.id
    assert ticket.subject == "借閱問題"
    assert ticket.config == {"priority": "normal"}
    msg = Message.objects.get(ticket=ticket)
    assert msg.content == "想了解續借規則"
    assert msg.sender_id == user.id
    assert msg.is_ai is False


def test_ticket_list_limits_to_request_user(auth_client, user, other_user):
    my_ticket = Ticket.objects.create(user=user, subject="我的客服單")
    Ticket.objects.create(user=other_user, subject="別人的客服單")
    url = reverse("chat-tickets")

    resp = auth_client.get(url)

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["id"] == my_ticket.id


def test_staff_can_list_all_and_filter_mine(staff_client, staff_user, user):
    mine = Ticket.objects.create(user=staff_user, subject="館員自派客服單")
    Ticket.objects.create(user=user, subject="一般使用者客服單")
    url = reverse("chat-tickets")

    resp_all = staff_client.get(url)
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert data_all["count"] == 2

    resp_mine = staff_client.get(f"{url}?mine=true")
    assert resp_mine.status_code == 200
    data_mine = resp_mine.json()
    assert data_mine["count"] == 1
    assert data_mine["results"][0]["id"] == mine.id


def test_message_post_requires_owner(auth_client, user, other_user):
    ticket = Ticket.objects.create(user=user, subject="續借問題")
    url = reverse("chat-messages")
    payload = {"ticket_id": ticket.id, "content": "請問可以續借嗎？"}

    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    resp_forbidden = other_client.post(url, payload, format="json")
    assert resp_forbidden.status_code == 403
    assert Message.objects.filter(ticket=ticket).count() == 0

    resp = auth_client.post(url, payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticket"] == ticket.id
    assert Message.objects.filter(ticket=ticket).count() == 1


def test_admin_patch_can_close_and_assign_ticket(staff_client, staff_user, user):
    assignee = staff_user
    ticket = Ticket.objects.create(user=user, subject="設備異常")
    url = reverse("chat-admin-ticket-patch", kwargs={"ticket_id": ticket.id})
    payload = {"status": Ticket.Status.CLOSED, "assignee_id": assignee.id}

    resp = staff_client.patch(url, payload, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == Ticket.Status.CLOSED
    assert data["assignee"] == assignee.id

    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.CLOSED
    assert ticket.assignee_id == assignee.id
    assert ticket.closed_at is not None


def test_ai_reply_creates_ai_message(monkeypatch, auth_client, user):
    ticket = Ticket.objects.create(user=user, subject="AI 助理測試")

    def fake_chat_once(messages):
        return "這裡是 AI 回覆"

    monkeypatch.setattr("chat.views.chat_once", fake_chat_once)
    url = reverse("chat-ai-reply")
    payload = {"ticket_id": ticket.id, "content": "請協助查詢借閱紀錄"}

    resp = auth_client.post(url, payload, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "這裡是 AI 回覆"

    messages = list(Message.objects.filter(ticket=ticket).order_by("created_at"))
    assert len(messages) == 2
    assert messages[0].is_ai is False and messages[0].sender_id == user.id
    assert messages[1].is_ai is True
    assert messages[1].response_meta.get("model") == "ollama"


def test_message_post_rejects_closed_ticket(auth_client, user):
    ticket = Ticket.objects.create(user=user, subject="維修狀態")
    ticket.close()
    url = reverse("chat-messages")
    payload = {"ticket_id": ticket.id, "content": "還可以更新嗎？"}

    resp = auth_client.post(url, payload, format="json")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Ticket is closed."
    assert Message.objects.filter(ticket=ticket).count() == 0


def test_staff_can_post_to_closed_ticket(staff_client, staff_user, user):
    ticket = Ticket.objects.create(user=user, subject="更新通知")
    ticket.close()
    url = reverse("chat-messages")
    payload = {"ticket_id": ticket.id, "content": "館員補充說明"}

    resp = staff_client.post(url, payload, format="json")

    assert resp.status_code == 201
    data = resp.json()
    assert data["ticket"] == ticket.id
    assert data["is_ai"] is False
    assert Message.objects.filter(ticket=ticket).count() == 1


@pytest.mark.service
def test_assistant_reply_without_tool(monkeypatch, user):
    ticket = Ticket.objects.create(user=user, subject="AI 測試")

    def fake_build(history, user_text, **kwargs):
        assert history == []
        assert user_text == "請提供資訊"
        return [{"role": "user", "content": user_text}]

    calls = []

    def fake_chat_once(msgs):
        calls.append(list(msgs))
        return "這裡是一般回覆"

    monkeypatch.setattr("chat.services.agent.build_messages", fake_build)
    monkeypatch.setattr("chat.services.agent.chat_once", fake_chat_once)

    reply, meta = assistant_reply(
        ticket=ticket,
        user_text="請提供資訊",
        use_rag=False,
        enable_tools=False,
        user=user,
    )

    assert reply == "這裡是一般回覆"
    assert meta["tool_called"] is False
    assert meta["used_rag"] is False
    assert len(calls) == 1


@pytest.mark.service
def test_assistant_reply_with_tool(monkeypatch, user):
    ticket = Ticket.objects.create(user=user, subject="工具測試")

    def fake_build(history, user_text, **kwargs):
        return [{"role": "user", "content": user_text}]

    chat_responses = iter(
        [
            '[TOOL] {"action": "lookup_book", "params": {"isbn": "978986"} }',
            "已取得館藏資訊",
        ]
    )
    calls = []

    def fake_chat_once(msgs):
        snapshot = [dict(item) for item in msgs]
        calls.append(snapshot)
        return next(chat_responses)

    def fake_search_topk(query, k):
        assert query == "查詢館藏"
        return [{"title": "圖書館使用手冊"}]

    def fake_tool(params):
        assert params == {"isbn": "978986"}
        return {"title": "Python Cookbook"}

    monkeypatch.setattr("chat.services.agent.build_messages", fake_build)
    monkeypatch.setattr("chat.services.agent.chat_once", fake_chat_once)
    monkeypatch.setattr("chat.services.agent.search_topk", fake_search_topk)
    monkeypatch.setattr("chat.services.agent.TOOLS_REGISTRY", {"lookup_book": fake_tool})

    reply, meta = assistant_reply(
        ticket=ticket,
        user_text="查詢館藏",
        use_rag=True,
        enable_tools=True,
        user=user,
    )

    assert reply == "已取得館藏資訊"
    assert meta["tool_called"] is True
    assert meta["tool_action"] == "lookup_book"
    assert meta["used_rag"] is True
    assert calls[1][-1]["content"].startswith('[TOOL_RESULT] {"title": "Python Cookbook"}')
