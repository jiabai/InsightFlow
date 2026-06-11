#!/bin/bash
# ============================================================
# InsightFlow 后端服务启动脚本 (macOS / Linux)
# 使用方式: bash src/server/scripts/start.sh
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "==> InsightFlow 后端服务启动"
echo "    项目目录: $PROJECT_ROOT"

# 切到项目根目录
cd "$PROJECT_ROOT"

# 检查 src/.env 是否存在
if [ ! -f "src/.env" ]; then
    echo "[ERROR] 配置文件 src/.env 不存在，请先创建并填写必要配置"
    exit 1
fi

# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
    echo "    虚拟环境已激活"
fi

# 加载 .env 中的配置
export $(grep -v '^\s*#' src/.env | grep -v '^\s*$' | grep -v '^VITE_' | xargs)
HOST=${SERVER_HOST:-0.0.0.0}
PORT=${SERVER_PORT:-8080}

# 设置 Python 路径并启动
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo "    启动地址: http://localhost:$PORT"
echo "    API 文档:  http://localhost:$PORT/docs"
echo ""

python -m uvicorn server.main:app --app-dir src --host "$HOST" --port "$PORT" --reload
