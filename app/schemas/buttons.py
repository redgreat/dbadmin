from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import ButtonType


class ButtonBase(BaseModel):
    name: str
    code: str
    type: ButtonType
    menu_id: int
    api_id: Optional[int] = None
    desc: Optional[str] = None
    order: int = 0
    is_hidden: bool = False


class ButtonCreate(ButtonBase):
    pass


class ButtonUpdate(ButtonBase):
    pass


class ButtonRead(ButtonBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: str
    updated_at: str
