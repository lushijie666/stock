# 股票量化交易系统 - CentOS 服务器部署指南

## 📋 目录

- [系统要求](#系统要求)
- [部署架构](#部署架构)
- [快速部署](#快速部署)
- [详细步骤](#详细步骤)
- [运维管理](#运维管理)
- [故障排查](#故障排查)
- [安全加固](#安全加固)
- [性能优化](#性能优化)

---

## 系统要求

### 服务器配置

| 配置项 | 最低要求 | 推荐配置 |
|--------|---------|---------|
| CPU | 2核 | 4核+ |
| 内存 | 2GB | 4GB+ |
| 硬盘 | 20GB | 50GB+ SSD |
| 系统 | CentOS 7/8 | CentOS 8 Stream |
| 网络 | 1Mbps | 10Mbps+ |

### 软件版本

- CentOS 7.x 或 8.x
- PostgreSQL 14+
- Python 3.9+
- Nginx 1.20+（可选，用于反向代理）

---

## 部署架构

```
Internet
    ↓
[Nginx (80/443)] ← 可选，用于反向代理和HTTPS
    ↓
[Streamlit App (8502)]
    ↓
[PostgreSQL (5432)]
```

---

## 快速部署

### 一键部署脚本

```bash
# 1. 下载并执行自动部署脚本
curl -o deploy.sh https://your-server.com/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

---

## 详细步骤

### 步骤 1: 系统准备

#### 1.1 更新系统

```bash
# 更新系统软件包
sudo yum update -y

# 安装基础工具
sudo yum install -y wget curl vim git unzip
```

#### 1.2 设置防火墙

```bash
# 启动防火墙
sudo systemctl start firewalld
sudo systemctl enable firewalld

# 开放必要端口
sudo firewall-cmd --permanent --add-port=8502/tcp  # Streamlit应用
sudo firewall-cmd --permanent --add-port=5432/tcp  # PostgreSQL（仅内网）
sudo firewall-cmd --permanent --add-port=80/tcp    # HTTP（可选）
sudo firewall-cmd --permanent --add-port=443/tcp   # HTTPS（可选）

# 重载防火墙
sudo firewall-cmd --reload

# 查看开放的端口
sudo firewall-cmd --list-ports
```

#### 1.3 关闭 SELinux（可选）

```bash
# 临时关闭
sudo setenforce 0

# 永久关闭
sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# 查看状态
getenforce
```

---

### 步骤 2: 安装 PostgreSQL 14

#### 2.1 添加 PostgreSQL 官方仓库

```bash
# 安装PostgreSQL仓库RPM
sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-$(rpm -E %{rhel})-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# 禁用内置PostgreSQL模块（CentOS 8）
sudo dnf -qy module disable postgresql
```

#### 2.2 安装 PostgreSQL 14

```bash
# 安装PostgreSQL 14服务端和客户端
sudo yum install -y postgresql14-server postgresql14

# 初始化数据库
sudo /usr/pgsql-14/bin/postgresql-14-setup initdb

# 启动PostgreSQL服务
sudo systemctl start postgresql-14
sudo systemctl enable postgresql-14

# 查看服务状态
sudo systemctl status postgresql-14
```

#### 2.3 配置 PostgreSQL

**修改认证方式**

```bash
# 编辑pg_hba.conf文件
sudo vim /var/lib/pgsql/14/data/pg_hba.conf
```

找到以下行：
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            ident
```

修改为：
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
host    all             all             0.0.0.0/0               md5
```

**修改监听地址**

```bash
# 编辑postgresql.conf
sudo vim /var/lib/pgsql/14/data/postgresql.conf
```

找到并修改：
```conf
listen_addresses = '*'          # 监听所有网络接口
port = 5432                      # 默认端口
max_connections = 100            # 最大连接数
shared_buffers = 256MB           # 共享内存缓冲区
```

**重启PostgreSQL**

```bash
sudo systemctl restart postgresql-14
```

#### 2.4 创建数据库和用户

```bash
# 切换到postgres用户
sudo -u postgres psql

# 在psql命令行中执行以下SQL
```

```sql
-- 创建数据库用户
CREATE USER stock_user WITH PASSWORD 'YourStrongPassword123!';

-- 创建数据库
CREATE DATABASE stock OWNER stock_user ENCODING 'UTF8';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE stock TO stock_user;

-- 退出
\q
```

**测试连接**

```bash
# 使用新用户连接数据库
psql -h localhost -U stock_user -d stock -W
```

输入密码后，如果能成功连接，说明配置正确。

---

### 步骤 3: 安装 Python 3.9+

#### 3.1 安装 Python 3.9

```bash
# CentOS 7 需要添加EPEL和IUS仓库
sudo yum install -y epel-release
sudo yum install -y https://repo.ius.io/ius-release-el7.rpm

# 安装Python 3.9
sudo yum install -y python39 python39-devel python39-pip

# 验证安装
python3.9 --version
pip3.9 --version
```

#### 3.2 安装系统依赖

```bash
# 安装PostgreSQL开发包（编译psycopg2需要）
sudo yum install -y postgresql14-devel

# 安装编译工具
sudo yum install -y gcc gcc-c++ make

# 安装其他依赖
sudo yum install -y openssl-devel libffi-devel bzip2-devel
```

---

### 步骤 4: 部署应用

#### 4.1 创建应用目录

```bash
# 创建应用用户（推荐）
sudo useradd -m -s /bin/bash stockapp

# 切换到应用用户
sudo su - stockapp

# 创建应用目录
mkdir -p ~/stock-app
cd ~/stock-app
```

#### 4.2 上传项目文件

**方法1: 使用Git（推荐）**

```bash
# 克隆仓库
git clone https://github.com/yourusername/stock-app.git .

# 或者如果是私有仓库
git clone https://your-git-server.com/stock-app.git .
```

**方法2: 使用SCP上传**

在本地开发机器上执行：

```bash
# 打包项目（在项目根目录执行）
tar -czf stock-app.tar.gz \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='*.log' \
    .

# 上传到服务器
scp stock-app.tar.gz stockapp@your-server-ip:~/

# 在服务器上解压
cd ~/stock-app
tar -xzf ../stock-app.tar.gz
```

**方法3: 使用SFTP**

使用FileZilla、WinSCP等工具上传项目文件。

#### 4.3 配置环境变量

```bash
# 创建.env文件
cat > .env << EOF
DB_USER=stock_user
DB_PASS=YourStrongPassword123!
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock
EOF

# 设置文件权限（保护敏感信息）
chmod 600 .env
```

#### 4.4 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python3.9 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

**常见问题处理**

如果安装 `psycopg2-binary` 失败：

```bash
# 确认已安装PostgreSQL开发包
sudo yum list installed | grep postgresql14-devel

# 如果未安装
sudo yum install -y postgresql14-devel

# 重新安装
pip install psycopg2-binary
```

#### 4.5 创建Streamlit配置

```bash
# 创建配置目录
mkdir -p .streamlit

# 创建配置文件
cat > .streamlit/config.toml << EOF
[server]
port = 8502
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = true

[browser]
serverAddress = "your-server-ip"
serverPort = 8502

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[global]
dataFrameSerialization = "legacy"
EOF
```

#### 4.6 初始化数据库

```bash
# 测试数据库连接
python3.9 << EOF
from config.database import check_db
try:
    check_db()
    print("✅ 数据库连接成功，表创建完成")
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
EOF
```

---

### 步骤 5: 启动应用

#### 5.1 测试运行

```bash
# 激活虚拟环境
source .venv/bin/activate

# 前台测试运行
streamlit run app.py --server.port 8502

# 按 Ctrl+C 停止
```

访问 `http://your-server-ip:8502` 测试是否正常。

#### 5.2 后台运行（使用脚本）

项目自带的 `start.sh` 脚本：

```bash
# 赋予执行权限
chmod +x start.sh

# 启动应用
./start.sh

# 查看日志
tail -f stock_app.log

# 查看进程
ps aux | grep streamlit
```

#### 5.3 使用 Systemd 服务（推荐）

创建systemd服务文件：

```bash
# 退出stockapp用户
exit

# 创建服务文件
sudo vim /etc/systemd/system/stock-app.service
```

添加以下内容：

```ini
[Unit]
Description=Stock Trading Quantitative System
After=network.target postgresql-14.service
Requires=postgresql-14.service

[Service]
Type=simple
User=stockapp
Group=stockapp
WorkingDirectory=/home/stockapp/stock-app
Environment="PATH=/home/stockapp/stock-app/.venv/bin"
ExecStart=/home/stockapp/stock-app/.venv/bin/streamlit run app.py --server.port 8502
Restart=always
RestartSec=10
StandardOutput=append:/home/stockapp/stock-app/logs/app.log
StandardError=append:/home/stockapp/stock-app/logs/error.log

[Install]
WantedBy=multi-user.target
```

创建日志目录：

```bash
sudo -u stockapp mkdir -p /home/stockapp/stock-app/logs
```

启动服务：

```bash
# 重载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start stock-app

# 设置开机自启
sudo systemctl enable stock-app

# 查看状态
sudo systemctl status stock-app

# 查看日志
sudo journalctl -u stock-app -f
```

---

### 步骤 6: 配置 Nginx 反向代理（可选）

#### 6.1 安装 Nginx

```bash
# 安装Nginx
sudo yum install -y nginx

# 启动Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### 6.2 配置反向代理

```bash
# 创建配置文件
sudo vim /etc/nginx/conf.d/stock-app.conf
```

添加以下内容：

```nginx
# HTTP 配置
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或IP

    # 访问日志
    access_log /var/log/nginx/stock-app-access.log;
    error_log /var/log/nginx/stock-app-error.log;

    # 上传大小限制
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_http_version 1.1;

        # WebSocket支持（Streamlit需要）
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 代理头设置
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        proxy_pass http://127.0.0.1:8502;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 6.3 配置 HTTPS（推荐）

**使用Let's Encrypt免费证书**

```bash
# 安装certbot
sudo yum install -y certbot python3-certbot-nginx

# 获取证书（自动配置Nginx）
sudo certbot --nginx -d your-domain.com

# 测试自动续期
sudo certbot renew --dry-run

# 设置自动续期任务
sudo crontab -e
# 添加以下行
0 3 * * * /usr/bin/certbot renew --quiet
```

**手动配置HTTPS**

修改 Nginx 配置：

```nginx
# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL证书
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 其他配置同HTTP
    location / {
        proxy_pass http://127.0.0.1:8502;
        # ... 其他代理配置
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

#### 6.4 重启 Nginx

```bash
# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx

# 查看状态
sudo systemctl status nginx
```

---

## 运维管理

### 服务管理

```bash
# 启动服务
sudo systemctl start stock-app

# 停止服务
sudo systemctl stop stock-app

# 重启服务
sudo systemctl restart stock-app

# 查看状态
sudo systemctl status stock-app

# 查看实时日志
sudo journalctl -u stock-app -f

# 查看最近的日志
sudo journalctl -u stock-app -n 100
```

### 数据库管理

```bash
# 连接数据库
sudo -u postgres psql -d stock

# 备份数据库
sudo -u postgres pg_dump stock > /backup/stock_$(date +%Y%m%d).sql

# 恢复数据库
sudo -u postgres psql stock < /backup/stock_20240101.sql

# 查看数据库大小
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('stock'));"

# 查看表大小
sudo -u postgres psql -d stock -c "\dt+"
```

### 自动备份脚本

```bash
# 创建备份脚本
sudo vim /usr/local/bin/backup-stock-db.sh
```

```bash
#!/bin/bash

# 备份目录
BACKUP_DIR="/backup/stock-db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/stock_$DATE.sql"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
sudo -u postgres pg_dump stock > $BACKUP_FILE

# 压缩备份
gzip $BACKUP_FILE

# 删除30天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

# 记录日志
echo "[$(date)] 数据库备份完成: $BACKUP_FILE.gz" >> /var/log/stock-backup.log
```

```bash
# 赋予执行权限
sudo chmod +x /usr/local/bin/backup-stock-db.sh

# 添加定时任务（每天凌晨2点备份）
sudo crontab -e
# 添加以下行
0 2 * * * /usr/local/bin/backup-stock-db.sh
```

### 日志管理

```bash
# 应用日志
tail -f /home/stockapp/stock-app/logs/app.log

# 错误日志
tail -f /home/stockapp/stock-app/logs/error.log

# Nginx访问日志
sudo tail -f /var/log/nginx/stock-app-access.log

# Nginx错误日志
sudo tail -f /var/log/nginx/stock-app-error.log

# PostgreSQL日志
sudo tail -f /var/lib/pgsql/14/data/log/postgresql-*.log
```

**日志轮转配置**

```bash
# 创建日志轮转配置
sudo vim /etc/logrotate.d/stock-app
```

```
/home/stockapp/stock-app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 stockapp stockapp
    sharedscripts
}
```

---

## 故障排查

### 常见问题

#### 1. 应用无法启动

```bash
# 查看服务状态
sudo systemctl status stock-app

# 查看详细日志
sudo journalctl -u stock-app -xe

# 检查端口占用
sudo netstat -tulpn | grep 8502

# 手动测试
sudo -u stockapp bash
cd ~/stock-app
source .venv/bin/activate
streamlit run app.py
```

#### 2. 数据库连接失败

```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql-14

# 测试连接
psql -h localhost -U stock_user -d stock -W

# 查看PostgreSQL日志
sudo tail -f /var/lib/pgsql/14/data/log/postgresql-*.log

# 检查防火墙
sudo firewall-cmd --list-ports
```

#### 3. 页面无法访问

```bash
# 检查Nginx状态
sudo systemctl status nginx

# 测试Nginx配置
sudo nginx -t

# 查看Nginx日志
sudo tail -f /var/log/nginx/error.log

# 检查防火墙
sudo firewall-cmd --list-ports

# 测试端口
curl -I http://localhost:8502
```

#### 4. 内存不足

```bash
# 查看内存使用
free -h

# 查看进程内存
ps aux --sort=-%mem | head -10

# 创建swap交换空间
sudo dd if=/dev/zero of=/swapfile bs=1G count=4
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 性能监控

```bash
# 实时监控
htop

# 系统资源
vmstat 1

# 磁盘IO
iostat -x 1

# 网络流量
iftop
```

---

## 安全加固

### 1. 配置防火墙

```bash
# 仅允许特定IP访问
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="your-ip" port port="8502" protocol="tcp" accept'

# 移除公开访问
sudo firewall-cmd --permanent --remove-port=8502/tcp

# 重载
sudo firewall-cmd --reload
```

### 2. PostgreSQL 安全

```bash
# 修改pg_hba.conf，仅允许本地连接
sudo vim /var/lib/pgsql/14/data/pg_hba.conf
```

```
# 仅允许本地连接
host    stock    stock_user    127.0.0.1/32    md5
```

```bash
# 重启PostgreSQL
sudo systemctl restart postgresql-14
```

### 3. 配置 fail2ban

```bash
# 安装fail2ban
sudo yum install -y fail2ban

# 创建配置
sudo vim /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
```

```bash
# 启动fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

### 4. 定期更新

```bash
# 自动安全更新
sudo yum install -y yum-cron
sudo systemctl start yum-cron
sudo systemctl enable yum-cron
```

---

## 性能优化

### 1. PostgreSQL 优化

```bash
# 编辑配置
sudo vim /var/lib/pgsql/14/data/postgresql.conf
```

```conf
# 内存设置（根据服务器内存调整）
shared_buffers = 512MB          # 约25%的系统内存
effective_cache_size = 2GB      # 约50-75%的系统内存
work_mem = 16MB
maintenance_work_mem = 128MB

# 连接设置
max_connections = 100

# WAL设置
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# 查询优化
random_page_cost = 1.1
effective_io_concurrency = 200
```

### 2. 应用优化

在 `.streamlit/config.toml` 中添加：

```toml
[server]
maxUploadSize = 200
maxMessageSize = 200

[runner]
magicEnabled = false
fastReruns = true
```

### 3. Nginx 优化

```nginx
# 在http块中添加
http {
    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript;

    # 连接优化
    keepalive_timeout 65;
    keepalive_requests 100;

    # 缓存
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m;
}
```

---

## 一键部署脚本

创建完整的自动化部署脚本：

```bash
sudo vim /root/deploy-stock-app.sh
```

内容请参考附件 `deploy-stock-app.sh`（下一个文件）

---

## 总结

完成以上步骤后，你的股票量化交易系统将：

- ✅ 运行在 CentOS 服务器上
- ✅ 使用 PostgreSQL 14 数据库
- ✅ 通过 Systemd 自动启动和管理
- ✅ 使用 Nginx 反向代理（可选HTTPS）
- ✅ 具备自动备份和日志管理
- ✅ 配置了基本的安全措施

**下一步**：
1. 访问 `http://your-server-ip:8502` 或 `https://your-domain.com`
2. 首次登录需要设置管理员账户
3. 更新股票列表数据
4. 开始使用系统进行量化分析

**技术支持**：
- 查看项目文档：`/home/stockapp/stock-app/docs/`
- 查看日志：`/home/stockapp/stock-app/logs/`
- 问题反馈：提交 Issue 到项目仓库
