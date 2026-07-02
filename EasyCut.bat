@echo off
chcp 65001 >nul
title EasyCut 易剪辑 v2.9 启动器

echo ══════════════════════════════════════════════════════════════
echo           🎬 EasyCut 易剪辑 v2.9 启动器
echo          AI 智能视频剪辑 · 一键启动 · 即开即用
echo ══════════════════════════════════════════════════════════════
echo.

:: 获取脚本所在目录
cd /d "%~dp0"

:: 检查 Python
echo [EasyCut] 检查 Python 环境...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [EasyCut] 错误: 未找到 Python！请先安装 Python 3.9+
    echo [EasyCut] 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [EasyCut] Python %PYTHON_VERSION% ✓

:: 检查 FFmpeg
echo [EasyCut] 检查 FFmpeg 环境...
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo [EasyCut] 警告: 未找到 FFmpeg，视频处理功能可能受限
    echo [EasyCut] 安装方法: 下载 https://ffmpeg.org/download.html
) else (
    echo [EasyCut] FFmpeg ✓
)

:: 创建虚拟环境
if not exist "venv" (
    echo [EasyCut] 首次运行，正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [EasyCut] 错误: 创建虚拟环境失败！
        pause
        exit /b 1
    )
    echo [EasyCut] 虚拟环境创建成功 ✓
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 检查依赖
echo [EasyCut] 检查依赖包...
python -c "import fastapi" >nul 2>nul
if %errorlevel% neq 0 (
    echo [EasyCut] 正在安装依赖（首次运行需要下载，请稍候）...
    pip install -r requirements.txt --quiet --disable-pip-version-check
    if %errorlevel% neq 0 (
        echo [EasyCut] 尝试使用镜像源...
        pip install -r requirements.txt --quiet --index-url https://mirrors.aliyun.com/pypi/simple/
    )
    echo [EasyCut] 依赖安装完成 ✓
) else (
    echo [EasyCut] 依赖包已就绪 ✓
)

:: 创建目录
echo [EasyCut] 检查目录结构...
if not exist "uploads" mkdir uploads
if not exist "output" mkdir output
if not exist "assets\music" mkdir assets\music
if not exist "uploads\covers" mkdir uploads\covers
if not exist "uploads\logos" mkdir uploads\logos
if not exist "uploads\luts" mkdir uploads\luts
echo [EasyCut] 目录结构就绪 ✓

:: 启动服务
echo.
echo ══════════════════════════════════════════════════════════════
echo   🌐 服务地址: http://127.0.0.1:9090
echo   📱 支持浏览器: Chrome / Edge / Firefox
echo   ⏹️  停止服务: 关闭此窗口
echo ══════════════════════════════════════════════════════════════
echo.

:: 延迟打开浏览器
start /b cmd /c "timeout /t 3 >nul && start http://127.0.0.1:9090"

:: 启动服务器
python web_server.py

:: 服务器退出后
echo.
echo [EasyCut] EasyCut 服务已停止
pause
