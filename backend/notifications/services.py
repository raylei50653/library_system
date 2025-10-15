from typing import Optional
from django.db import transaction
from .models import Notification


@transaction.atomic
def create_notification(*, user, notif_type: str, message: str, loan: Optional[object] = None) -> Notification:
    """建立一筆通知；由 loans 服務或排程呼叫。"""
    return Notification.objects.create(
        user=user,
        type=notif_type,
        message=message,
        loan=loan,
    )


def mark_as_read(*, notification_id: int, user) -> Optional[Notification]:
    notif = Notification.objects.filter(id=notification_id, user=user).first()
    if notif and not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=["is_read"])
    return notif


def mark_all_as_read(*, user) -> int:
    qs = Notification.objects.filter(user=user, is_read=False)
    updated = qs.update(is_read=True)
    return updated