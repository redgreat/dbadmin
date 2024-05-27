#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @author by wangcw 
# @generate at 2024/5/27 下午2:38

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OperationBase(BaseModel):
    id: int
    user_id: int = Field(description="操作用户Id")
    user_name: str = Field(description="操作用户姓名")
    status_code: int = Field(description="状态编码")
    client_ip: str = Field(description="请求客户端地址")
    request_method: str = Field(description="请求方法")
    api_path: str = Field(description="请求API地址")
    system: str = Field(description="客户端操作系统")
    browser: str = Field(description="请求浏览器")
    summary: str = Field(description="操作用户姓名")
    route_name: str = Field(description="路由名称")
    description: str = Field(description="描述")
    tags: Optional[list] = Field([], description="标签")
    process_time: float = Field(description="处理时长")
    params: str = Field(description="调用参数")
    logtime: Optional[datetime] = Field(description="日志写入时间")
