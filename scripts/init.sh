#!/usr/bin/env bash
# tradecat Pro 初始化脚本
# 用法: ./scripts/init.sh [service-name]
# 示例: ./scripts/init.sh          # 初始化全部
#       ./scripts/init.sh data-service  # 初始化单个

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SERVICES=(data-service trading-service telegram-service order-service)

# ==================== 工具函数 ====================
success() { echo -e "\033[0;32m✓ $1\033[0m"; }
fail() { echo -e "\033[0;31m✗ $1\033[0m"; exit 1; }
info() { echo -e "\033[0;34m→ $1\033[0m"; }

# ==================== 初始化单个服务 ====================
init_service() {
    local svc="$1"
    local svc_dir="$ROOT/services/$svc"
    
    if [ ! -d "$svc_dir" ]; then
        fail "服务目录不存在: $svc_dir"
    fi
    
    echo ""
    echo "=== 初始化 $svc ==="
    cd "$svc_dir"
    
    # 1. 创建虚拟环境
    if [ ! -d ".venv" ]; then
        info "创建虚拟环境..."
        python3 -m venv .venv
    else
        info "虚拟环境已存在"
    fi
    
    # 2. 安装依赖
    info "安装依赖..."
    source .venv/bin/activate
    pip install -q --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -q -r requirements.txt
    elif [ -f "pyproject.toml" ]; then
        pip install -q -e .
    fi
    
    # 3. 创建配置文件（权限 600）
    if [ -f "config/.env.example" ] && [ ! -f "config/.env" ]; then
        cp config/.env.example config/.env
        chmod 600 config/.env
        info "已创建 config/.env（权限 600，请编辑填入真实配置）"
    fi
    
    # 4. 创建运行时目录
    mkdir -p pids logs
    
    # 5. 设置脚本权限
    [ -f "scripts/start.sh" ] && chmod +x scripts/start.sh
    
    deactivate 2>/dev/null || true
    success "$svc 初始化完成"
}

# ==================== 系统依赖检查 ====================
check_system() {
    echo "=== 系统依赖检查 ==="
    
    # Python
    if command -v python3 &>/dev/null; then
        success "Python3: $(python3 --version)"
    else
        fail "Python3 未安装"
    fi
    
    # pip
    if command -v pip3 &>/dev/null; then
        success "pip3: $(pip3 --version | cut -d' ' -f2)"
    else
        fail "pip3 未安装"
    fi
    
    # TA-Lib (可选)
    if python3 -c "import talib" 2>/dev/null; then
        success "TA-Lib: 已安装"
    else
        info "TA-Lib: 未安装（K线形态检测需要）"
        echo "  安装: sudo apt install libta-lib-dev && pip install TA-Lib"
    fi
    
    # PostgreSQL client (可选)
    if command -v psql &>/dev/null; then
        success "psql: $(psql --version | head -1)"
    else
        info "psql: 未安装（数据库操作需要）"
    fi
}

# ==================== 创建全局目录 ====================
init_global() {
    echo ""
    echo "=== 创建全局目录 ==="
    mkdir -p "$ROOT/run" "$ROOT/logs" "$ROOT/backups"
    chmod +x "$ROOT/scripts/"*.sh 2>/dev/null || true
    success "全局目录已创建"
}

# ==================== 入口 ====================
if [ -n "${1:-}" ]; then
    # 初始化单个服务
    init_service "$1"
else
    # 初始化全部
    check_system
    init_global
    
    for svc in "${SERVICES[@]}"; do
        init_service "$svc"
    done
    
    echo ""
    echo "=========================================="
    echo -e "\033[0;32m全部初始化完成\033[0m"
    echo "=========================================="
    echo ""
    echo "下一步："
    echo "  1. 编辑各服务的 config/.env 文件"
    echo "  2. 启动服务: ./scripts/start.sh daemon"
    echo "  3. 查看状态: ./scripts/start.sh status"
fi
