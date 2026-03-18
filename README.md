# DBAdmin - 数据运维管理平台

基于 FastAPI + Vue3 + Naive UI 的现代化前后端分离开发平台，融合了 RBAC 权限管理、动态路由和 JWT 鉴权。

## 特性

- **高性能技术栈**：Python 3.12 + FastAPI 异步框架 + Vue3 + Vite
- **动态路由**：后端动态路由，结合 RBAC 权限模型，提供精细的菜单路由控制
- **JWT鉴权**：使用 JSON Web Token 进行身份验证和授权
- **细粒度权限控制**：按钮和接口级别的权限控制
- **Docker部署**：支持一键 Docker 部署

## 快速开始

### 方法一：Docker Hub 拉取镜像

```sh
docker pull redgreat/dbadmin:latest 
docker run -d --restart=always --name=dbadmin -p 8090:80 redgreat/dbadmin
```

### 方法二：Dockerfile 构建镜像

```sh
git clone https://github.com/redgreat/dbadmin.git
cd dbadmin
docker build --no-cache . -t dbadmin
docker run -d --restart=always --name=dbadmin -p 8090:80 dbadmin
```

访问 http://localhost:8090，默认账号：admin / 123456

## 本地开发

### 后端

环境要求：Python 3.12 + [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)

```sh
# 安装依赖
poetry install

# 启动服务
make run
# 或
poetry run python run.py
```

后端服务运行在 http://localhost:8090，API文档：http://localhost:8090/docs

### 前端

环境要求：Node.js 18+

```sh
cd web
npm install
npm run dev
```

前端开发服务运行在 http://localhost:5180

## 项目结构

```
├── app/                    # 后端应用
│   ├── api/                # API路由
│   ├── controllers/        # 控制器
│   ├── core/               # 核心功能(配置、依赖、中间件等)
│   ├── models/             # 数据模型
│   ├── schemas/            # Pydantic模型
│   ├── services/           # 业务服务
│   └── settings/           # 配置设置
├── config/                 # 配置文件
│   └── config.yml          # 主配置文件
├── deploy/                 # 部署配置
│   ├── supervisord_with_nginx.conf
│   ├── app_supervisor_with_nginx.conf
│   └── web.conf            # Nginx配置模板
├── log/                    # 日志目录
├── script/                 # 辅助脚本
│   ├── dockerbuild.ps1     # Docker构建脚本
│   ├── docker-local-restart.ps1
│   └── run-dev.ps1         # 本地开发启动脚本
├── scripts/                # 数据库迁移和管理脚本
├── tests/                  # 测试文件
├── web/                    # 前端应用
│   ├── src/                # 源代码
│   ├── public/             # 静态资源
│   └── build/              # 构建配置
├── Dockerfile              # 生产环境Dockerfile
├── DockerfileLocal         # 本地开发Dockerfile
├── docker-compose.yml      # 生产环境编排
├── docker-compose-local.yml # 本地开发编排
├── Makefile                # Make命令
├── pyproject.toml          # Python项目配置
└── run.py                  # 开发环境启动脚本
```

## Make 命令

```sh
make install     # 安装依赖
make run         # 启动服务
make check       # 代码检查
make format      # 代码格式化
make test        # 运行测试
```

## 配置

主配置文件位于 `config/config.yml`，首次运行前请复制示例配置：

```sh
cp config/config.yml.example config/config.yml
```

## License

MIT
