param(
  [switch]$NewWindow
)

<#
  停止正在运行的前后端进程
#>
function Stop-RunningProcesses {
  param()

  Write-Host "正在检查并停止运行中的进程..." -ForegroundColor Yellow

  # 停止后端进程 (通过端口8090)
  $port8090Process = Get-NetTCPConnection -LocalPort 8090 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
  if ($port8090Process) {
    foreach ($procId in $port8090Process) {
      try {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "已停止后端进程 (PID: $procId, 端口 8090)" -ForegroundColor Green
      } catch {}
    }
    Start-Sleep -Seconds 1
  } else {
    Write-Host "未发现后端进程 (端口 8090)" -ForegroundColor Gray
  }

  # 停止前端进程 (通过端口5180)
  $port5180Process = Get-NetTCPConnection -LocalPort 5180 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
  if ($port5180Process) {
    foreach ($procId in $port5180Process) {
      try {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "已停止前端进程 (PID: $procId, 端口 5180)" -ForegroundColor Green
      } catch {}
    }
    Start-Sleep -Seconds 1
  } else {
    Write-Host "未发现前端进程 (端口 5180)" -ForegroundColor Gray
  }
}

<#
  启动后端开发服务器
#>
function Start-Backend {
  param()
  $root = (Split-Path $PSScriptRoot -Parent)
  $logDir = Join-Path $root "log"
  if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
  }
  $logFile = Join-Path $logDir "backend.log"

  Write-Host "正在启动后端服务..." -ForegroundColor Cyan
  Write-Host "  日志文件: $logFile" -ForegroundColor Gray

  $args = @('-m','uvicorn','app:app','--reload','--port','8090')

  if ($NewWindow) {
    $p = Start-Process -FilePath 'python' -ArgumentList $args -WorkingDirectory $root -PassThru
  } else {
    # 在后台启动，日志输出到文件
    $p = Start-Process -FilePath 'python' -ArgumentList $args -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.error"
  }
  return $p
}

<#
  构建前端项目
#>
function Build-Frontend {
  param()
  $web = Join-Path (Split-Path $PSScriptRoot -Parent) 'web'

  $npm = Get-Command npm -ErrorAction SilentlyContinue
  $node = Get-Command node -ErrorAction SilentlyContinue
  if (-not $npm -or -not $node) {
    throw '未检测到 Node 或 npm，请确认已安装 Node.js 并将其加入 PATH'
  }

  Write-Host "正在构建前端项目..." -ForegroundColor Cyan
  Write-Host "  工作目录: $web" -ForegroundColor Gray

  # 执行前端构建
  $buildProcess = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', 'npm', 'run', 'build') -WorkingDirectory $web -NoNewWindow -Wait -PassThru

  if ($buildProcess.ExitCode -eq 0) {
    Write-Host "✓ 前端构建完成" -ForegroundColor Green
  } else {
    Write-Host "✗ 前端构建失败 (退出码: $($buildProcess.ExitCode))" -ForegroundColor Red
    throw "前端构建失败"
  }
}

<#
  启动前端开发服务器
#>
function Start-Frontend {
  param()
  $web = Join-Path (Split-Path $PSScriptRoot -Parent) 'web'
  $root = (Split-Path $PSScriptRoot -Parent)
  $logDir = Join-Path $root "log"
  if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
  }
  $logFile = Join-Path $logDir "frontend.log"

  $npm = Get-Command npm -ErrorAction SilentlyContinue
  $node = Get-Command node -ErrorAction SilentlyContinue
  if (-not $npm -or -not $node) {
    throw '未检测到 Node 或 npm，请确认已安装 Node.js 并将其加入 PATH'
  }

  Write-Host "正在启动前端服务..." -ForegroundColor Cyan
  Write-Host "  日志文件: $logFile" -ForegroundColor Gray

  # Windows 上 npm 是一个 cmd 文件，需要通过 cmd.exe 执行
  $cmdArgs = @('/c', 'npm', 'run', 'dev')
  if ($NewWindow) {
    $p = Start-Process -FilePath 'cmd.exe' -ArgumentList $cmdArgs -WorkingDirectory $web -PassThru
  } else {
    # 在后台启动，日志输出到文件
    $p = Start-Process -FilePath 'cmd.exe' -ArgumentList $cmdArgs -WorkingDirectory $web -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.error"
  }
  return $p
}

<#
  同时启动前后端并输出进程信息
#>
function Run-All {
  param()

  # 先停止运行中的进程
  Stop-RunningProcesses

  Write-Host ""
  Write-Host "========================================" -ForegroundColor White
  Write-Host "  启动开发环境" -ForegroundColor White
  Write-Host "========================================" -ForegroundColor White
  Write-Host ""

  # 先构建前端
  Build-Frontend
  Write-Host ""

  $backend = Start-Backend
  Start-Sleep -Seconds 2  # 等待后端启动

  $frontend = Start-Frontend

  Write-Host ""
  Write-Host "✓ 后端服务已启动" -ForegroundColor Green
  Write-Host "  PID: $($backend.Id)" -ForegroundColor Gray
  Write-Host "  地址: http://localhost:8090" -ForegroundColor Gray
  Write-Host "  文档: http://localhost:8090/docs" -ForegroundColor Gray
  Write-Host ""
  Write-Host "✓ 前端服务已启动" -ForegroundColor Green
  Write-Host "  PID: $($frontend.Id)" -ForegroundColor Gray
  Write-Host "  地址: http://localhost:5180" -ForegroundColor Gray
  Write-Host ""
  Write-Host "========================================" -ForegroundColor White
  Write-Host "  按 Ctrl+C 停止所有服务" -ForegroundColor Yellow
  Write-Host "========================================" -ForegroundColor White
  Write-Host ""

  if (-not $NewWindow) {
    # 在当前窗口保持运行，监听Ctrl+C
    try {
      while ($true) {
        Start-Sleep -Seconds 1
      }
    }
    finally {
      Write-Host ""
      Write-Host "正在停止服务..." -ForegroundColor Yellow
      Stop-RunningProcesses
      Write-Host "服务已停止" -ForegroundColor Green
    }
  }
}

Run-All
