# AGENTS.md — AI 开发入口

本文件是 AI 编码助手（Zed / Cursor / Codex / Trae / Kiro 等）进入本项目（DBAdmin 数据运维平台）的**统一入口与权威规范**。任何自动化或人工的代码改动，都必须先阅读本文件，并遵循其中引用的详细文档。

> 详细文档位于 `docs/` 目录：
> - 开发总览与常用命令：本文「常用命令」章节
> - 后端开发规范：[`docs/backend-standards.md`](docs/backend-standards.md)
> - 前端开发规范：[`docs/frontend-standards.md`](docs/frontend-standards.md)
> - 数据库开发规范：[`docs/database-standards.md`](docs/database-standards.md)
> - **新增一个完整模块的完整步骤**：[`docs/module-addition-guide.md`](docs/module-addition-guide.md)

---

## 1. 项目简介

DBAdmin 是一个基于 **FastAPI + Vue3 + Naive UI** 的现代化前后端分离数据库运维管理平台，核心能力包括：RBAC 权限管理、后端动态路由、JWT 鉴权、按钮/接口级权限控制、数据库连接管理、定时任务、报表导出、AI Agent（MCP）。

### 技术栈

| 层 | 技术 |
| --- | --- |
| 后端语言 | Python 3.12 |
| 后端框架 | FastAPI 0.139 + Uvicorn |
| ORM | Tortoise ORM 0.20.1（异步） |
| 数据校验 | Pydantic v2 / pydantic-settings |
| 迁移工具 | Aerich |
| 任务队列 | Celery + Redis + APScheduler |
| 日志 | Loguru |
| 前端框架 | Vue 3（Composition API + `<script setup>`） |
| 构建工具 | Vite 4 |
| UI 组件库 | Naive UI |
| 状态管理 | Pinia |
| 路由 | Vue Router 4（后端动态路由） |
| 样式 | UnoCSS（原子化）+ Sass |
| 工具库 | VueUse、Axios、Day.js、Vue-I18n |

### 目录结构

```
dbadmin/
├── app/                        # 后端应用
│   ├── api/v1/                 # API 路由（每个模块一个文件夹）
│   ├── controllers/            # 控制器（继承 CRUDBase，业务逻辑）
│   ├── core/                   # 核心：crud、dependency、exceptions、middlewares、config_loader、init_app
│   ├── models/                 # Tortoise ORM 模型
│   ├── schemas/                # Pydantic 模型（Create/Update/Out）
│   ├── services/               # 业务服务（连接池、导出、同步等）
│   ├── settings/               # 配置（从 config/config.yml 读取）
│   ├── tasks/                  # Celery 任务
│   └── utils/                  # jwt、password、encryption、audit
├── aiagent/                    # AI Agent / MCP 服务
├── config/
│   └── config.yml(.example)    # 统一配置文件（**勿提交真实 config.yml**）
├── migrations/                 # Aerich 迁移文件
├── scripts/                    # 数据库迁移与管理脚本
├── tests/                      # pytest 测试
├── web/                        # 前端应用
│   ├── src/
│   │   ├── api/                # 所有后端接口封装（index.js）
│   │   ├── views/              # 页面（每个模块一个文件夹/index.vue）
│   │   ├── components/         # 公共组件（page/table/query-bar/icon）
│   │   ├── composables/        # useCRUD 等组合式函数
│   │   ├── router/             # 路由（basicRoutes + 动态路由）
│   │   ├── store/              # Pinia（permission/user/app/tags）
│   │   ├── utils/              # http、storage、auth、common
│   │   ├── styles/             # 样式（Sass/全局）
│   │   ├── layout/             # 布局（侧边栏/顶栏等）
│   │   └── directives/         # 自定义指令（v-permission）
│   ├── build/                  # Vite 构建配置
│   └── i18n/                   # 国际化（cn.json / en.json）
├── deploy/                     # 部署配置（nginx/supervisor）
├── docs/                       # 开发文档（本目录）
├── run.py                      # 开发启动脚本
├── Makefile                    # make 命令
├── pyproject.toml              # Python 依赖与工具配置
└── docker-compose*.yml         # 容器编排
```

---

## 2. 快速开始 / 常用命令

### 后端

```sh
poetry install          # 安装依赖
make run                # 启动（等价 poetry run python run.py），监听 8090
make check              # 代码检查（black + isort + ruff）
make format             # 代码格式化（black + isort）
make test               # 运行测试
make migrate            # aerich migrate（生成迁移文件）
make upgrade            # aerich upgrade（应用迁移）
```

首次运行前复制配置：`cp config/config.yml.example config/config.yml`。API 文档：`http://localhost:8090/docs`。

### 前端

```sh
cd web
npm install
npm run dev             # 开发服务，监听 5180
npm run build           # 生产构建
npm run lint            # ESLint 检查
npm run lint:fix        # ESLint 自动修复
npm run prettier        # Prettier 格式化
```

---

## 3. 硬性规则（红线，必须遵守）

1. **配置安全**：`config/config.yml` 含密钥与数据库口令，**绝不提交到 Git**，只维护 `config/config.yml.example`。密钥、口令、Token 一律走配置文件或数据库，禁止硬编码在源码中。
2. **数据库连接口令**：`conn` 表中保存的是**加密后的密码**，读写必须经过 `app/utils/encryption.py`，禁止明文存取。
3. **接口权限**：新增受保护接口必须注册进 `app/api/v1/__init__.py` 并挂 `dependencies=[DependPermisson]`；同时必须在数据库建立 `menu` → `menu_api` → `api` 的授权关系，否则前端按钮不可见、接口 403。
4. **响应格式统一**：所有接口返回 `Success` / `Fail` / `SuccessExtra`（见 `app/schemas/base.py`），禁止直接 `return dict`。
5. **模型注册**：新增 Model 必须在 `app/models/__init__.py` 中 `from .xxx import *`，否则 Aerich 不会识别该表。
6. **删除菜单/模型/表**属于破坏性操作，执行前必须确认并提示用户备份（可用 `backup_table` 思路）。
7. **不破坏用户既有改动**：只做任务要求内的改动，不顺手重构无关代码。
8. **提交规范**：遵循 Conventional Commits，`feat(模块): 中文描述`，主题≤50 字符、命令式、结尾无标点。参考 `git log`。
9. **不要自动 `git commit` / 建分支**，除非用户明确要求。

---

## 4. 后端规范速览

> 完整版见 [`docs/backend-standards.md`](docs/backend-standards.md)

- **分层**：`api/v1`（路由，只做参数校验与返回）→ `controllers`（业务逻辑，继承 `CRUDBase`）→ `services`（跨模块/外部服务）→ `models`（数据访问）。
- **Controller**：继承 `CRUDBase[Model, Create, Update]`，文件末尾导出单例 `xxx_controller = XxxController()`，并在 `app/controllers/__init__.py` 导出。
- **Schema**：Pydantic v2，命名 `XxxCreate` / `XxxUpdate` / `XxxOut`，字段用 `Field(..., description=...)`，`Update` 的 `id` 必填。
- **异步**：所有 DB 操作 `async/await`，禁止在异步路径中写阻塞 IO。
- **查询**：Tortoise 查询表达式 `Q()` 组合过滤；分页统一 `offset((page-1)*page_size).limit(page_size)`。
- **异常**：抛 `HTTPException`，已在 `app/core/exceptions.py` 统一处理；业务错误返回 `Fail`。
- **日志**：用 `app.log` 的 `logger` 或标准 `logging.getLogger(__name__)`。

---

## 5. 前端规范速览

> 完整版见 [`docs/frontend-standards.md`](docs/frontend-standards.md)

- **组合式 API**：统一 `<script setup>`，`defineOptions({ name: '中文名' })`，且该 `name` 必须与后端菜单 `name` 一致（影响 keep-alive）。
- **UI**：Naive UI 组件（`NButton` 等，模板里用小写 `n-button`），图标用 `TheIcon`，页面用 `CommonPage` 包裹，表格/弹窗用 `CrudTable` / `CrudModal` + `useCRUD`。
- **接口**：集中在 `web/src/api/index.js`，通过 `request.get/post/...`；组件内统一 `import api from '@/api'`。
- **权限**：按钮用 `v-permission="'post/api/v1/模块/动作'"` 控制显隐。
- **样式**：优先 UnoCSS 原子类，复杂样式用 `<style scoped>`（Sass）。
- **别名**：`@` → `web/src`，`~` → `web`。自动导入已配置（Vue API、Naive UI、api 等按需）。
- **文件路径**：菜单 `component` 字段指向 `/src/views/<模块>/index.vue`，前端通过 `import.meta.glob('@/views/**/index.vue')` 动态匹配，因此页面文件名必须为 `index.vue`。

---

## 6. 数据库规范速览

> 完整版见 [`docs/database-standards.md`](docs/database-standards.md)

- 模型继承 `BaseModel`（自带 `BigIntField` 主键 `id` 与 `to_dict`）+ `TimestampMixin`（`created_at` / `updated_at`）。
- 表名用 `Meta.table` 指定，业务表建议 `sys_` 前缀或见现有约定（`user`、`role`、`menu`、`conn`、`sys_dict`）。
- 字段必须写 `description`；需要检索的字段加 `index=True`；唯一字段加 `unique=True`。
- 软删除：保留 `deleted`（`BooleanField`）+ `deleted_at`（`DatetimeField`），查询默认 `filter(deleted=False)`。
- 枚举用 `CharEnumField`；关联用 `ForeignKeyField` / `ManyToManyField` 并指定 `related_name`。
- **改模型后必须生成迁移**：`make migrate` → `make upgrade`（或 `poetry run aerich migrate && poetry run aerich upgrade`）。
- 系统管理库为 `default` 连接；业务库连接在 `conn` 表中动态管理，SQL 尽量通过 ORM，复杂统计 SQL 需注释并防止注入（参数化）。

---

## 7. 新增一个完整模块的标准流程

> 带代码模板的**完整步骤**见 [`docs/module-addition-guide.md`](docs/module-addition-guide.md)。下面为最小 checklist：

**后端**
1. `app/models/<模块>.py` 定义模型 → 在 `app/models/__init__.py` 导入。
2. `app/schemas/<模块>.py` 定义 `Create` / `Update` / `Out`。
3. `app/controllers/<模块>.py` 继承 `CRUDBase` → 在 `app/controllers/__init__.py` 导出单例。
4. `app/api/v1/<模块>/<模块>.py` 写路由，`__init__.py` 导出 `<模块>_router` → 在 `app/api/v1/__init__.py` 以 `prefix` + `tags` + `dependencies=[DependPermisson]` 注册。
5. `make migrate && make upgrade` 生成并应用迁移。

**菜单与权限**（RBAC 关键，缺一不可）
6. 在数据库插入 `menu` 记录（`component` 指向 `/src/views/<模块>/index.vue`）。
7. 插入 `api` 记录（`method` + `path`，如 `POST /api/v1/<模块>/create`）。
8. 插入 `menu_api` 关联；并把菜单授予目标 `role`。可参考 `app/core/init_app.py::ensure_oa_menus` 的编程式做法，或提供 SQL 脚本放入 `scripts/`。

**前端**
9. `web/src/api/index.js` 增加接口方法。
10. 新建 `web/src/views/<模块>/index.vue`（`defineOptions({ name })` 与菜单名一致）。
11. 按钮加 `v-permission`；如走国际化则在 `web/i18n/messages/cn.json` 与 `en.json` 补文案。

---

## 8. 自检清单（提交前）

- [ ] 后端 `make check` 通过（black / isort / ruff）。
- [ ] 前端 `npm run lint` 通过。
- [ ] 新增/改动模型已 `make migrate && make upgrade`。
- [ ] 新接口已注册路由并配好 `menu`/`api`/`menu_api` 授权。
- [ ] 新接口返回 `Success/Fail/SuccessExtra`，前端能正确解析 `{ code, msg, data }`。
- [ ] 未提交 `config/config.yml` 等含密钥文件。
- [ ] 相关文档（`docs/`）已同步更新。

---

## 9. 给 AI 助手的特别提示

- 修改跨前后端的模块时，**前后端一起改**（接口、页面、菜单、权限四件套齐全）。
- 遇到拿不准的既有实现，先用 `grep` / `read_file` 查证，不要臆造 API 或路径。
- 生成数据库 DDL / 迁移前，先确认目标库类型（`config.yml` 的 `database.admin.engine`：postgres/mysql/sqlite）。
- 若需求模糊或属于破坏性操作（删表、删菜单、批量改数），先向用户确认再执行。
