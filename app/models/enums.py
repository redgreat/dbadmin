from enum import Enum, StrEnum


class EnumBase(Enum):
    @classmethod
    def get_member_values(cls):
        return [item.value for item in cls._member_map_.values()]

    @classmethod
    def get_member_names(cls):
        return [name for name in cls._member_names_]


class MethodType(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ButtonType(StrEnum):
    ADD = "add"         # 新增
    EDIT = "edit"       # 编辑
    DELETE = "delete"   # 删除
    EXPORT = "export"   # 导出
    IMPORT = "import"   # 导入
    DOWNLOAD = "download" # 下载
    UPLOAD = "upload"   # 上传
    VIEW = "view"       # 查看
    SUBMIT = "submit"   # 提交
    APPROVE = "approve" # 审批
    REJECT = "reject"   # 拒绝
    CUSTOM = "custom"   # 自定义
