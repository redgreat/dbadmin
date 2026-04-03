from datetime import datetime
from typing import Optional, Tuple

from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.models.alert import AlertSender, AlertSendLog
from app.schemas.alert import AlertSenderCreate, AlertSenderUpdate, AlertLogCreate


class AlertSenderController(CRUDBase[AlertSender, AlertSenderCreate, AlertSenderUpdate]):
    def __init__(self):
        super().__init__(model=AlertSender)

    async def check_name_exists(self, sender_name: str, exclude_id: Optional[int] = None) -> bool:
        query = self.model.filter(sender_name=sender_name)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def list_with_filter(
        self,
        page: int,
        page_size: int,
        sender_name: Optional[str] = None,
        channel_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> Tuple[int, list[AlertSender]]:
        search = Q()
        if sender_name:
            search &= Q(sender_name__icontains=sender_name)
        if channel_type:
            search &= Q(channel_type=channel_type)
        if is_enabled is not None:
            search &= Q(is_enabled=is_enabled)
        return await self.list(page=page, page_size=page_size, search=search, order=["-updated_at", "-id"])


class AlertLogController(CRUDBase[AlertSendLog, AlertLogCreate, AlertLogCreate]):
    def __init__(self):
        super().__init__(model=AlertSendLog)

    async def create_log(self, log_in: AlertLogCreate):
        obj_data = log_in.model_dump(exclude_none=True)
        if not obj_data.get("sent_at"):
            obj_data["sent_at"] = datetime.now()
        obj = self.model(**obj_data)
        await obj.save()
        return obj

    async def list_with_filter(
        self,
        page: int,
        page_size: int,
        sender_id: Optional[int] = None,
        sender_name: Optional[str] = None,
        channel_type: Optional[str] = None,
        send_status: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Tuple[int, list[AlertSendLog]]:
        search = Q()
        if sender_id:
            search &= Q(sender_id=sender_id)
        if sender_name:
            search &= Q(sender_name__icontains=sender_name)
        if channel_type:
            search &= Q(channel_type=channel_type)
        if send_status is not None:
            search &= Q(send_status=send_status)
        if start_time:
            search &= Q(sent_at__gte=start_time)
        if end_time:
            search &= Q(sent_at__lte=end_time)
        return await self.list(page=page, page_size=page_size, search=search, order=["-sent_at", "-id"])


alert_sender_controller = AlertSenderController()
alert_log_controller = AlertLogController()
