from typing import Optional
from app.models.imptask import ImpTask
from app.core.crud import CRUDBase


class ImpTaskController(CRUDBase[ImpTask, None, None]):
    """Excel导入任务控制器"""

    def __init__(self):
        super().__init__(model=ImpTask)

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        """获取任务列表"""
        query = self.model.all()

        if task_name:
            query = query.filter(task_name__icontains=task_name)

        if status:
            query = query.filter(status=status)

        if user_id:
            query = query.filter(user_id=user_id)

        total = await query.count()
        items = await query.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)

        return items, total


imptask_controller = ImpTaskController()
