# 本地调试Docker镜像启动脚本
# 功能：构建前端 -> 停止旧容器 -> 删除旧镜像 -> 清空日志 -> 构建新镜像 -> 启动新容器

# 设置控制台编码为UTF-8
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 项目根目录
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Green
Write-Host "本地调试Docker镜像启动脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# 0. 构建前端
Write-Host ""
Write-Host "[0/6] 构建前端..." -ForegroundColor Yellow
Set-Location web

# 检查 node_modules 是否存在
if (-not (Test-Path "node_modules")) {
    Write-Host "  安装前端依赖..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "× 前端依赖安装失败！" -ForegroundColor Red
        exit 1
    }
}

# 构建前端
Write-Host "  编译前端代码..." -ForegroundColor Cyan
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "× 前端构建失败！" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot
Write-Host "√ 前端构建完成" -ForegroundColor Green

# 1. 停止并删除旧容器
Write-Host ""
Write-Host "[1/6] 停止并删除旧容器..." -ForegroundColor Yellow
$containers = docker-compose -f docker-compose-local.yml ps -q 2>$null
if ($containers) {
    docker-compose -f docker-compose-local.yml down
    Write-Host "√ 旧容器已停止并删除" -ForegroundColor Green
} else {
    Write-Host "! 没有运行中的容器" -ForegroundColor Yellow
}

# 2. 删除旧镜像
Write-Host ""
Write-Host "[2/6] 删除旧镜像..." -ForegroundColor Yellow
$imageExists = docker images dbadmin:local --format "{{.ID}}" 2>$null
if ($imageExists) {
    docker rmi -f dbadmin:local
    Write-Host "√ 旧镜像已删除" -ForegroundColor Green
} else {
    Write-Host "! 没有找到旧镜像" -ForegroundColor Yellow
}

# 3. 清空日志文件夹
Write-Host ""
Write-Host "[3/6] 清空日志文件夹..." -ForegroundColor Yellow
$logPath = Join-Path $ProjectRoot "log"
if (Test-Path $logPath) {
    # 删除日志文件夹中的所有文件
    $logFiles = Get-ChildItem -Path $logPath -File -ErrorAction SilentlyContinue
    if ($logFiles) {
        $logFiles | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "√ 已清空 $($logFiles.Count) 个日志文件" -ForegroundColor Green
    } else {
        Write-Host "! 日志文件夹为空" -ForegroundColor Yellow
    }
} else {
    Write-Host "! 日志文件夹不存在" -ForegroundColor Yellow
}

# 4. 构建新镜像
Write-Host ""
Write-Host "[4/6] 构建新镜像..." -ForegroundColor Yellow
docker-compose -f docker-compose-local.yml build
# 取消缓存机制构建
# docker-compose -f docker-compose-local.yml build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "× 镜像构建失败！" -ForegroundColor Red
    exit 1
}
Write-Host "√ 新镜像构建完成" -ForegroundColor Green

# 5. 启动新容器
Write-Host ""
Write-Host "[5/6] 启动新容器..." -ForegroundColor Yellow
docker-compose -f docker-compose-local.yml up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "× 容器启动失败！" -ForegroundColor Red
    exit 1
}
Write-Host "√ 容器已启动" -ForegroundColor Green

# 显示容器状态
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "容器状态" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
docker-compose -f docker-compose-local.yml ps

# 显示日志提示
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "查看日志: docker-compose -f docker-compose-local.yml logs -f"
Write-Host "停止服务: docker-compose -f docker-compose-local.yml down"
Write-Host "访问地址: http://localhost:8091"
