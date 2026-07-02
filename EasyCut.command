#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# EasyCut 易剪辑 - 一键启动脚本
# 双击此文件即可启动 EasyCut 服务
# ═══════════════════════════════════════════════════════════════

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[EasyCut]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[EasyCut]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[EasyCut]${NC} $1"
}

print_error() {
    echo -e "${RED}[EasyCut]${NC} $1"
}

# 清屏并显示欢迎信息
clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🎬 EasyCut 易剪辑 v2.9 启动器                   ║"
echo "║         AI 智能视频剪辑 · 一键启动 · 即开即用             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查 Python 版本
print_info "检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    PYTHON_CMD="python"
else
    print_error "未找到 Python！请先安装 Python 3.9+"
    print_info "下载地址: https://www.python.org/downloads/"
    read -p "按回车键退出..."
    exit 1
fi

# 检查 Python 版本是否满足要求
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    print_error "Python 版本过低: $PYTHON_VERSION"
    print_info "EasyCut 需要 Python 3.9+，请升级 Python"
    read -p "按回车键退出..."
    exit 1
fi
print_success "Python $PYTHON_VERSION ✓"

# 检查 FFmpeg
print_info "检查 FFmpeg 环境..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    print_success "FFmpeg $FFMPEG_VERSION ✓"
else
    print_warning "未找到 FFmpeg，视频处理功能可能受限"
    print_info "安装方法: brew install ffmpeg"
fi

# 创建虚拟环境（如果不存在）
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    print_info "首次运行，正在创建虚拟环境..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        print_error "创建虚拟环境失败！"
        read -p "按回车键退出..."
        exit 1
    fi
    print_success "虚拟环境创建成功 ✓"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 检查并安装依赖
print_info "检查依赖包..."
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    # 检查是否需要安装依赖
    if ! $PYTHON_CMD -c "import fastapi, uvicorn, cv2, yaml" &> /dev/null; then
        print_info "正在安装依赖（首次运行需要下载，请稍候）..."
        pip install -r "$REQUIREMENTS_FILE" --quiet --disable-pip-version-check
        if [ $? -ne 0 ]; then
            print_warning "部分依赖安装失败，尝试使用镜像源..."
            pip install -r "$REQUIREMENTS_FILE" --quiet --index-url https://mirrors.aliyun.com/pypi/simple/
        fi
        print_success "依赖安装完成 ✓"
    else
        print_success "依赖包已就绪 ✓"
    fi
fi

# 创建必要的目录
print_info "检查目录结构..."
for dir in "uploads" "output" "assets/music" "uploads/covers" "uploads/logos" "uploads/luts"; do
    mkdir -p "$SCRIPT_DIR/$dir"
done
print_success "目录结构就绪 ✓"

# 检查端口是否被占用
PORT=9090
if command -v lsof &> /dev/null; then
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_warning "端口 $PORT 已被占用，尝试使用其他端口..."
        PORT=9091
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            PORT=9092
        fi
    fi
fi

# 更新 web_server.py 中的端口
print_info "配置服务端口..."
sed -i '' "s/port=[0-9]*/port=$PORT/g" "$SCRIPT_DIR/web_server.py"

# 启动服务器
print_info "正在启动 EasyCut 服务..."
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🌐 服务地址: http://127.0.0.1:$PORT                      ║"
echo "║  📱 支持浏览器: Chrome / Safari / Firefox                  ║"
echo "║  ⏹️  停止服务: 关闭此终端窗口                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 延迟打开浏览器
(sleep 3 && open "http://127.0.0.1:$PORT") &

# 启动 FastAPI 服务器
$PYTHON_CMD web_server.py

# 如果服务器退出，显示提示
echo ""
print_info "EasyCut 服务已停止"
read -p "按回车键退出..."
