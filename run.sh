#!/bin/bash

# OCR启动脚本

echo "========================================"
echo "  OCR - 启动脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查虚拟环境是否存在
if [ ! -d "src/.venv" ]; then
    echo "❌ 虚拟环境不存在"
    echo ""
    echo "请先创建虚拟环境并安装依赖:"
    echo "  python3.12 -m venv src/.venv"
    echo "  source src/.venv/bin/activate"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  pip install -r requirements_macos.txt"
    else
        echo "  pip install -r requirements.txt"
    fi
    exit 1
fi

# 激活虚拟环境
echo "✓ 激活虚拟环境..."
source src/.venv/bin/activate

# 启动应用
echo "✓ 启动应用..."
echo ""
python src/app/app.py
