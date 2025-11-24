#!/bin/bash
set -e

echo "=========================================="
echo "  OCR - macOS 环境自动配置脚本"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/src/.venv"
REQ_FILE="$SCRIPT_DIR/requirements_macos.txt"
MIN_PYTHON_VERSION="3.10"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 requirements 文件是否存在
if [ ! -f "$REQ_FILE" ]; then
    echo -e "${RED}[错误]${NC} 找不到 $REQ_FILE"
    echo "请确保该文件随项目一起分发。"
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
echo "[步骤 1/5] 检测 Python 环境..."
PYTHON_CMD=""

for py_cmd in python3.12 python3.11 python3.10 python3 python; do
    if PYTHON_CMD=$(check_python_version "$py_cmd"); then
        PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1)
        echo -e "${GREEN}✓${NC} 找到可用的 Python: $PYTHON_VERSION ($PYTHON_CMD)"
        break
    fi
done

# 如果没有找到合适的 Python，尝试自动安装
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}[提示]${NC} 未找到 Python $MIN_PYTHON_VERSION+ 环境"
    echo ""
    echo "正在尝试自动安装 Python..."
    echo ""

    # 检查是否有 Homebrew
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}[提示]${NC} 未检测到 Homebrew 包管理器"
        echo ""
        echo "Homebrew 是 macOS 上最流行的包管理器，可以方便地安装 Python。"
        echo ""
        echo -e "${GREEN}[自动安装]${NC} 即将安装 Homebrew..."
        echo "安装过程中会要求您输入 macOS 用户密码（这是正常的）"
        echo ""
        read -p "按 Enter 继续安装 Homebrew，或按 Ctrl+C 取消..."

        # 安装 Homebrew
        echo ""
        echo "正在安装 Homebrew（可能需要几分钟）..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # 检查安装是否成功
        if ! command -v brew &> /dev/null; then
            # 对于 Apple Silicon Mac，Homebrew 安装在 /opt/homebrew
            if [ -f "/opt/homebrew/bin/brew" ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            # 对于 Intel Mac，Homebrew 安装在 /usr/local
            elif [ -f "/usr/local/bin/brew" ]; then
                eval "$(/usr/local/bin/brew shellenv)"
            else
                echo -e "${RED}[错误]${NC} Homebrew 安装失败"
                echo "请手动安装 Homebrew 后重新运行本脚本："
                echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
        fi

        echo -e "${GREEN}✓${NC} Homebrew 安装成功"
    else
        echo -e "${GREEN}✓${NC} 检测到 Homebrew: $(brew --version | head -1)"
    fi

    # 使用 Homebrew 安装 Python
    echo ""
    echo "[步骤 1.5/5] 安装 Python 3.12..."
    echo "正在通过 Homebrew 安装 Python（可能需要几分钟）..."

    if brew install python@3.12; then
        echo -e "${GREEN}✓${NC} Python 安装成功"

        # 重新检测 Python
        for py_cmd in python3.12 python3 python; do
            if PYTHON_CMD=$(check_python_version "$py_cmd"); then
                PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1)
                echo -e "${GREEN}✓${NC} 已激活: $PYTHON_VERSION ($PYTHON_CMD)"
                break
            fi
        done

        if [ -z "$PYTHON_CMD" ]; then
            echo -e "${RED}[错误]${NC} Python 安装成功但无法找到可执行文件"
            echo "请尝试重新打开终端窗口后再次运行本脚本"
            exit 1
        fi
    else
        echo -e "${RED}[错误]${NC} Python 安装失败"
        echo "请检查网络连接或手动安装 Python："
        echo "  brew install python@3.12"
        exit 1
    fi
fi

# 删除旧的虚拟环境（如果是非 macOS/Linux 格式）
if [ -d "$VENV_DIR" ]; then
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${YELLOW}[提示]${NC} 检测到非 Unix 虚拟环境，正在清理..."
        rm -rf "$VENV_DIR"
    fi
fi

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "[步骤 2/5] 创建虚拟环境..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误]${NC} 创建虚拟环境失败"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} 虚拟环境创建成功: $VENV_DIR"
else
    echo ""
    echo "[步骤 2/5] 虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
echo ""
echo "[步骤 3/5] 激活虚拟环境..."
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误]${NC} 激活虚拟环境失败"
    exit 1
fi
echo -e "${GREEN}✓${NC} 虚拟环境已激活"

# 升级 pip
echo ""
echo "[步骤 4/5] 升级 pip..."
python -m pip install --upgrade pip --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} pip 升级成功"
else
    echo -e "${YELLOW}[警告]${NC} pip 升级失败（可忽略）"
fi

# 安装依赖
echo ""
echo "[步骤 5/5] 安装项目依赖..."
echo "这可能需要几分钟，取决于网络速度和 CPU 性能..."
echo ""

python -m pip install --no-cache-dir -r "$REQ_FILE"
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[错误]${NC} 依赖安装失败"
    echo "请检查网络连接或尝试使用国内镜像源："
    echo "  python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r $REQ_FILE"
    exit 1
fi

# 完成
echo ""
echo "=========================================="
echo -e "${GREEN}✓ macOS 开发环境配置完成！${NC}"
echo "=========================================="
echo ""
echo "后续使用方法："
echo "  1. 双击 run.command 启动应用（开发模式）"
echo "  2. 或在终端执行: ./run.sh"
echo ""
echo "⚠️ 注意事项："
echo "  - macOS运行时监听 127.0.0.1:8143 (本地开发)"
echo "  - Input目录每5分钟自动清理"
echo "  - Output目录每天00:00自动清理"
echo ""
echo "部署到Linux服务器时请参考 README.md"
echo ""
