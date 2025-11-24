#!/bin/bash
set -e

echo "=========================================="
echo "  OCR - Linux服务器环境配置脚本"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/src/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MIN_PYTHON_VERSION="3.10"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 requirements 文件是否存在
if [ ! -f "$REQ_FILE" ]; then
    echo -e "${RED}[错误]${NC} 找不到 $REQ_FILE"
    echo "请确保该文件存在于项目根目录"
    exit 1
fi

# 检查 Python 版本是否满足要求
check_python_version() {
    local python_cmd="$1"
    if ! command -v "$python_cmd" &> /dev/null; then
        return 1
    fi

    local version=$("$python_cmd" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || echo "0.0")

    # 比较版本号
    local required_version=$(echo "$MIN_PYTHON_VERSION" | awk -F. '{printf "%d%02d", $1, $2}')
    local current_version=$(echo "$version" | awk -F. '{printf "%d%02d", $1, $2}')

    if [ "$current_version" -ge "$required_version" ]; then
        echo "$python_cmd"
        return 0
    fi
    return 1
}

# 检测系统中的 Python
echo "[步骤 1/6] 检测 Python 环境..."
PYTHON_CMD=""

for py_cmd in python3.12 python3.11 python3.10 python3 python; do
    if PYTHON_CMD=$(check_python_version "$py_cmd"); then
        PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1)
        echo -e "${GREEN}✓${NC} 找到可用的 Python: $PYTHON_VERSION ($PYTHON_CMD)"
        break
    fi
done

# 如果没有找到合适的 Python
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}[错误]${NC} 未找到 Python $MIN_PYTHON_VERSION+ 环境"
    echo ""
    echo "请先安装 Python 3.10 或更高版本:"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt update"
    echo "  sudo apt install -y python3.12 python3.12-venv python3-pip"
    echo ""
    echo "CentOS/RHEL:"
    echo "  sudo yum install -y python3.12 python3.12-venv"
    echo ""
    exit 1
fi

# 检查并安装系统依赖
echo ""
echo "[步骤 2/6] 检查系统依赖..."

# 检测包管理器
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
    echo "检测到 Debian/Ubuntu 系统"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "检测到 CentOS/RHEL 系统"
else
    PKG_MANAGER="unknown"
    echo -e "${YELLOW}[警告]${NC} 未知的包管理器，跳过系统依赖检查"
fi

# 安装中文字体(可选)
if [ "$PKG_MANAGER" = "apt" ]; then
    if ! dpkg -l | grep -q fonts-wqy-microhei; then
        echo "正在安装中文字体..."
        if [ "$EUID" -eq 0 ]; then
            apt-get install -y fonts-wqy-microhei fonts-noto-cjk 2>/dev/null || echo -e "${YELLOW}[警告]${NC} 中文字体安装失败(可忽略)"
        else
            echo -e "${YELLOW}[提示]${NC} 需要root权限安装中文字体，可稍后手动安装:"
            echo "  sudo apt install -y fonts-wqy-microhei fonts-noto-cjk"
        fi
    else
        echo -e "${GREEN}✓${NC} 中文字体已安装"
    fi
fi

# 删除旧的虚拟环境（如果是非 Unix 格式）
if [ -d "$VENV_DIR" ]; then
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${YELLOW}[提示]${NC} 检测到非 Unix 虚拟环境，正在清理..."
        rm -rf "$VENV_DIR"
    fi
fi

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "[步骤 3/6] 创建虚拟环境..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误]${NC} 创建虚拟环境失败"
        echo ""
        echo "可能需要安装 python3-venv 包:"
        if [ "$PKG_MANAGER" = "apt" ]; then
            echo "  sudo apt install -y python3-venv"
        elif [ "$PKG_MANAGER" = "yum" ]; then
            echo "  sudo yum install -y python3-venv"
        fi
        exit 1
    fi
    echo -e "${GREEN}✓${NC} 虚拟环境创建成功: $VENV_DIR"
else
    echo ""
    echo "[步骤 3/6] 虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
echo ""
echo "[步骤 4/6] 激活虚拟环境..."
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误]${NC} 激活虚拟环境失败"
    exit 1
fi
echo -e "${GREEN}✓${NC} 虚拟环境已激活"

# 升级 pip
echo ""
echo "[步骤 5/6] 升级 pip..."
python -m pip install --upgrade pip --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} pip 升级成功"
else
    echo -e "${YELLOW}[警告]${NC} pip 升级失败（可忽略）"
fi

# 配置pip镜像源(可选)
read -p "是否使用清华镜像源加速下载? (y/n, 默认y): " use_mirror
use_mirror=${use_mirror:-y}

if [[ "$use_mirror" =~ ^[Yy]$ ]]; then
    echo "配置pip使用清华镜像..."
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn
    echo -e "${GREEN}✓${NC} 镜像源配置成功"
fi

# 安装依赖
echo ""
echo "[步骤 6/6] 安装项目依赖..."
echo "=========================================="
echo "⚠️ 重要提示:"
echo "  - 依赖包数量: 约150个"
echo "  - 下载大小: 约3-5GB"
echo "  - 预计时间: 10-20分钟"
echo "=========================================="
echo ""
read -p "按 Enter 继续安装，或按 Ctrl+C 取消..."

python -m pip install -r "$REQ_FILE"
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[错误]${NC} 依赖安装失败"
    echo ""
    echo "请尝试使用镜像源重新安装:"
    echo "  source src/.venv/bin/activate"
    echo "  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
    exit 1
fi

# 完成
echo ""
echo "=========================================="
echo -e "${GREEN}✓ Linux服务器环境配置完成！${NC}"
echo "=========================================="
echo ""
echo "后续使用方法:"
echo ""
echo "1. 启动服务:"
echo "   ./run.sh"
echo ""
echo "2. 或后台运行:"
echo "   nohup ./run.sh > ocr.log 2>&1 &"
echo ""
echo "3. 访问地址:"
echo "   http://<服务器IP>:8143"
echo ""
echo "⚠️ 注意事项:"
echo "  - 确保防火墙已开放8143端口:"
echo "    sudo ufw allow 8143/tcp"
echo "  - Input目录每5分钟自动清理"
echo "  - Output目录每天00:00自动清理"
echo ""
echo "配置systemd服务(可选):"
echo "  详见 README.md 的服务器部署指南"
echo ""
