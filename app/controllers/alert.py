from datetime import datetime

from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.models.alert import AlertSender, AlertSendLog
from app.schemas.alert import AlertLogCreate, AlertSenderCreate, AlertSenderUpdate


class AlertSenderController(CRUDBase[AlertSender, AlertSenderCreate, AlertSenderUpdate]):
    def __init__(self):
        super().__init__(model=AlertSender)

    async def check_name_exists(self, sender_name: str, exclude_id: int | None = None) -> bool:
        query = self.model.filter(sender_name=sender_name)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def list_with_filter(
        self,
        page: int,
        page_size: int,
        sender_name: str | None = None,
        channel_type: str | None = None,
        is_enabled: bool | None = None,
    ) -> tuple[int, list[AlertSender]]:
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
        sender_id: int | None = None,
        sender_name: str | None = None,
        channel_type: str | None = None,
        send_status: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[int, list[AlertSendLog]]:
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
