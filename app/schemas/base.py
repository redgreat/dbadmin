from typing import Any, Generic, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

DataT = TypeVar("DataT")


class ResponseSchema(BaseModel, Generic[DataT]):
    """标准响应模式"""

    code: int = 200
    msg: str = "success"
    data: DataT | None = None


class Success(JSONResponse):
    def __init__(
        self,
        code: int = 200,
        msg: str | None = "OK",
        data: Any | None = None,
        **kwargs,
    ):
        content = {"code": code, "msg": msg, "data": data}
        content.update(kwargs)
        super().__init__(content=content, status_code=code)


class Fail(JSONResponse):
    def __init__(
        self,
        code: int = 400,
        msg: str | None = None,
        data: Any | None = None,
        **kwargs,
    ):
        content = {"code": code, "msg": msg, "data": data}
        content.update(kwargs)
        super().__init__(content=content, status_code=code)


class SuccessExtra(JSONResponse):
    def __init__(
        self,
        code: int = 200,
        msg: str | None = None,
        data: Any | None = None,
        total: int = 0,
        page: int = 1,
        page_size: int = 20,
        **kwargs,
    ):
        content = {
            "code": code,
            "msg": msg,
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
        content.update(kwargs)
        super().__init__(content=content, status_code=code)
