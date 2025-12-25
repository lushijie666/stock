#!/bin/bash

################################################################################
# 股票量化交易系统 - CentOS 一键部署脚本
#
# 功能：
#   - 自动安装 PostgreSQL 14
#   - 自动安装 Python 3.9
#   - 自动配置数据库
#   - 自动部署应用
#   - 自动配置 Systemd 服务
#
# 使用方法：
#   sudo bash deploy-stock-app.sh
#
# 作者：Stock App Team
# 版本：1.0.0
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
APP_USER="stockapp"
APP_DIR="/home/$APP_USER/stock-app"
DB_NAME="stock"
DB_USER="stock_user"
DB_PASS="StockApp@2024!"  # 建议修改为更强密码
PYTHON_VERSION="3.9"
APP_PORT="8502"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本必须以root权限运行"
        exit 1
    fi
}

# 检测系统版本
detect_os() {
    if [ -f /etc/redhat-release ]; then
        OS_VERSION=$(cat /etc/redhat-release)
        log_info "检测到系统: $OS_VERSION"

        if [[ $OS_VERSION == *"CentOS"* ]] || [[ $OS_VERSION == *"Red Hat"* ]]; then
            if [[ $OS_VERSION == *"release 7"* ]]; then
                OS_MAJOR_VERSION=7
            elif [[ $OS_VERSION == *"release 8"* ]]; then
                OS_MAJOR_VERSION=8
            else
                log_error "不支持的CentOS版本"
                exit 1
            fi
        else
            log_error "此脚本仅支持CentOS 7/8"
            exit 1
        fi
    else
        log_error "无法检测系统版本"
        exit 1
    fi
}

# 更新系统
update_system() {
    log_info "更新系统软件包..."
    yum update -y
    yum install -y wget curl vim git unzip
    log_success "系统更新完成"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."

    systemctl start firewalld
    systemctl enable firewalld

    firewall-cmd --permanent --add-port=$APP_PORT/tcp
    firewall-cmd --reload

    log_success "防火墙配置完成，已开放端口: $APP_PORT"
}

# 安装PostgreSQL 14
install_postgresql() {
    log_info "安装 PostgreSQL 14..."

    # 添加PostgreSQL仓库
    yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-${OS_MAJOR_VERSION}-x86_64/pgdg-redhat-repo-latest.noarch.rpm

    # CentOS 8 需要禁用内置模块
    if [ $OS_MAJOR_VERSION -eq 8 ]; then
        dnf -qy module disable postgresql
    fi

    # 安装PostgreSQL
    yum install -y postgresql14-server postgresql14 postgresql14-devel

    # 初始化数据库
    if [ ! -d "/var/lib/pgsql/14/data/base" ]; then
        /usr/pgsql-14/bin/postgresql-14-setup initdb
    fi

    # 启动服务
    systemctl start postgresql-14
    systemctl enable postgresql-14

    log_success "PostgreSQL 14 安装完成"
}

# 配置PostgreSQL
configure_postgresql() {
    log_info "配置 PostgreSQL..."

    # 备份原配置
    cp /var/lib/pgsql/14/data/pg_hba.conf /var/lib/pgsql/14/data/pg_hba.conf.bak
    cp /var/lib/pgsql/14/data/postgresql.conf /var/lib/pgsql/14/data/postgresql.conf.bak

    # 修改认证方式
    sed -i 's/host    all             all             127.0.0.1\/32            ident/host    all             all             127.0.0.1\/32            md5/' /var/lib/pgsql/14/data/pg_hba.conf

    # 修改监听地址
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/pgsql/14/data/postgresql.conf

    # 性能优化
    cat >> /var/lib/pgsql/14/data/postgresql.conf << EOF

# Performance tuning
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 128MB
max_connections = 100
EOF

    # 重启PostgreSQL
    systemctl restart postgresql-14

    log_success "PostgreSQL 配置完成"
}

# 创建数据库和用户
setup_database() {
    log_info "创建数据库和用户..."

    # 创建用户和数据库
    su - postgres << EOF
psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" || true
psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING 'UTF8';" || true
psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true
EOF

    # 测试连接
    if PGPASSWORD=$DB_PASS psql -h localhost -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
        log_success "数据库创建成功"
    else
        log_error "数据库连接测试失败"
        exit 1
    fi
}

# 安装Python 3.9
install_python() {
    log_info "安装 Python $PYTHON_VERSION..."

    if [ $OS_MAJOR_VERSION -eq 7 ]; then
        # CentOS 7
        yum install -y epel-release
        yum install -y https://repo.ius.io/ius-release-el7.rpm
        yum install -y python39 python39-devel python39-pip
    else
        # CentOS 8
        dnf install -y python39 python39-devel python39-pip
    fi

    # 安装编译依赖
    yum install -y gcc gcc-c++ make openssl-devel libffi-devel bzip2-devel

    # 验证安装
    python3.9 --version

    log_success "Python $PYTHON_VERSION 安装完成"
}

# 创建应用用户
create_app_user() {
    log_info "创建应用用户..."

    if ! id "$APP_USER" &>/dev/null; then
        useradd -m -s /bin/bash $APP_USER
        log_success "用户 $APP_USER 创建成功"
    else
        log_warning "用户 $APP_USER 已存在"
    fi
}

# 部署应用
deploy_application() {
    log_info "部署应用..."

    # 创建应用目录
    mkdir -p $APP_DIR
    chown $APP_USER:$APP_USER $APP_DIR

    # 这里需要根据实际情况选择部署方式
    # 方式1: 从Git克隆（需要配置GIT_REPO）
    # 方式2: 从当前目录复制
    # 方式3: 用户手动上传后，此脚本跳过

    log_warning "请确保应用代码已上传到: $APP_DIR"
    log_warning "如果还未上传，请按 Ctrl+C 退出，上传代码后重新运行"

    read -p "应用代码已准备好？ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "请上传应用代码到 $APP_DIR 后重新运行此脚本"
        exit 0
    fi

    # 设置权限
    chown -R $APP_USER:$APP_USER $APP_DIR

    log_success "应用部署准备完成"
}

# 配置应用
configure_application() {
    log_info "配置应用..."

    # 创建.env文件
    cat > $APP_DIR/.env << EOF
DB_USER=$DB_USER
DB_PASS=$DB_PASS
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
EOF

    chown $APP_USER:$APP_USER $APP_DIR/.env
    chmod 600 $APP_DIR/.env

    # 创建Streamlit配置
    mkdir -p $APP_DIR/.streamlit
    cat > $APP_DIR/.streamlit/config.toml << EOF
[server]
port = $APP_PORT
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = true

[browser]
serverPort = $APP_PORT

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[global]
dataFrameSerialization = "legacy"
EOF

    chown -R $APP_USER:$APP_USER $APP_DIR/.streamlit

    log_success "应用配置完成"
}

# 安装Python依赖
install_dependencies() {
    log_info "安装Python依赖..."

    su - $APP_USER << 'EOF'
cd ~/stock-app

# 创建虚拟环境
python3.9 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "警告: 未找到 requirements.txt"
    exit 1
fi

# 测试导入
python << PYTEST
try:
    from config.database import check_db
    check_db()
    print("✅ 数据库初始化成功")
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")
    exit(1)
PYTEST

EOF

    if [ $? -eq 0 ]; then
        log_success "Python依赖安装完成"
    else
        log_error "Python依赖安装失败"
        exit 1
    fi
}

# 创建日志目录
create_log_directory() {
    log_info "创建日志目录..."

    mkdir -p $APP_DIR/logs
    chown $APP_USER:$APP_USER $APP_DIR/logs

    log_success "日志目录创建完成"
}

# 配置Systemd服务
setup_systemd_service() {
    log_info "配置Systemd服务..."

    cat > /etc/systemd/system/stock-app.service << EOF
[Unit]
Description=Stock Trading Quantitative System
After=network.target postgresql-14.service
Requires=postgresql-14.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
ExecStart=$APP_DIR/.venv/bin/streamlit run app.py --server.port $APP_PORT
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/logs/app.log
StandardError=append:$APP_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

    # 重载systemd
    systemctl daemon-reload

    # 启动服务
    systemctl start stock-app
    systemctl enable stock-app

    # 等待服务启动
    sleep 5

    # 检查状态
    if systemctl is-active --quiet stock-app; then
        log_success "Systemd服务配置完成，应用已启动"
    else
        log_error "应用启动失败，请查看日志: journalctl -u stock-app -xe"
        exit 1
    fi
}

# 配置自动备份
setup_backup() {
    log_info "配置自动备份..."

    # 创建备份目录
    mkdir -p /backup/stock-db

    # 创建备份脚本
    cat > /usr/local/bin/backup-stock-db.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/backup/stock-db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/stock_$DATE.sql"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

su - postgres -c "pg_dump stock" > $BACKUP_FILE

gzip $BACKUP_FILE

find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] 数据库备份完成: $BACKUP_FILE.gz" >> /var/log/stock-backup.log
EOF

    chmod +x /usr/local/bin/backup-stock-db.sh

    # 添加定时任务
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-stock-db.sh") | crontab -

    log_success "自动备份配置完成（每天凌晨2点）"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "========================================="
    log_success "部署完成！"
    echo "========================================="
    echo ""
    echo "访问信息："
    echo "  应用地址: http://$(hostname -I | awk '{print $1}'):$APP_PORT"
    echo "  或者: http://your-domain.com:$APP_PORT"
    echo ""
    echo "服务管理："
    echo "  启动: sudo systemctl start stock-app"
    echo "  停止: sudo systemctl stop stock-app"
    echo "  重启: sudo systemctl restart stock-app"
    echo "  状态: sudo systemctl status stock-app"
    echo ""
    echo "日志查看："
    echo "  应用日志: tail -f $APP_DIR/logs/app.log"
    echo "  错误日志: tail -f $APP_DIR/logs/error.log"
    echo "  系统日志: sudo journalctl -u stock-app -f"
    echo ""
    echo "数据库信息："
    echo "  数据库: $DB_NAME"
    echo "  用户: $DB_USER"
    echo "  密码: $DB_PASS"
    echo "  连接: psql -h localhost -U $DB_USER -d $DB_NAME"
    echo ""
    echo "备份信息："
    echo "  备份目录: /backup/stock-db"
    echo "  备份时间: 每天凌晨2点"
    echo "  保留天数: 30天"
    echo ""
    echo "========================================="
    echo ""
}

# 主函数
main() {
    echo ""
    echo "========================================="
    echo "  股票量化交易系统 - 自动部署脚本"
    echo "========================================="
    echo ""

    check_root
    detect_os

    log_info "开始部署，这可能需要10-20分钟..."

    update_system
    setup_firewall
    install_postgresql
    configure_postgresql
    setup_database
    install_python
    create_app_user
    deploy_application
    configure_application
    install_dependencies
    create_log_directory
    setup_systemd_service
    setup_backup

    show_deployment_info
}

# 执行主函数
main "$@"
