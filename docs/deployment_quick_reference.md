# 股票量化交易系统 - 部署快速参考

## 🚀 快速部署（3步完成）

### 步骤 1: 准备服务器

```bash
# 连接到CentOS服务器
ssh root@your-server-ip

# 创建项目目录
mkdir -p /root/stock-deploy
cd /root/stock-deploy
```

### 步骤 2: 上传文件

**方式A: 使用SCP（推荐）**

在本地机器执行：
```bash
# 打包项目
cd /path/to/your/stock-project
tar -czf stock-app.tar.gz \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    .

# 上传到服务器
scp stock-app.tar.gz root@your-server-ip:/root/stock-deploy/
scp deploy-stock-app.sh root@your-server-ip:/root/stock-deploy/
```

**方式B: 使用Git**

在服务器上执行：
```bash
git clone https://github.com/your-username/stock-app.git
```

### 步骤 3: 运行部署脚本

```bash
# 赋予执行权限
chmod +x deploy-stock-app.sh

# 如果是打包文件，先解压
tar -xzf stock-app.tar.gz -C /home/stockapp/stock-app/

# 运行部署脚本
./deploy-stock-app.sh
```

等待10-20分钟，脚本会自动完成：
- ✅ 安装PostgreSQL 14
- ✅ 创建数据库和用户
- ✅ 安装Python 3.9
- ✅ 安装应用依赖
- ✅ 配置Systemd服务
- ✅ 启动应用

完成后访问：`http://your-server-ip:8502`

---

## 📝 手动部署步骤（详细版）

### 1. 安装PostgreSQL

```bash
# 添加仓库
yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# 安装PostgreSQL 14
yum install -y postgresql14-server postgresql14

# 初始化并启动
/usr/pgsql-14/bin/postgresql-14-setup initdb
systemctl start postgresql-14
systemctl enable postgresql-14

# 创建数据库
sudo -u postgres psql << EOF
CREATE USER stock_user WITH PASSWORD 'your_password';
CREATE DATABASE stock OWNER stock_user;
GRANT ALL PRIVILEGES ON DATABASE stock TO stock_user;
\q
EOF
```

### 2. 安装Python 3.9

```bash
# 添加仓库
yum install -y epel-release
yum install -y https://repo.ius.io/ius-release-el7.rpm

# 安装Python
yum install -y python39 python39-devel python39-pip

# 安装编译工具
yum install -y gcc gcc-c++ postgresql14-devel
```

### 3. 部署应用

```bash
# 创建用户
useradd -m stockapp

# 上传代码到 /home/stockapp/stock-app/

# 切换用户
su - stockapp
cd ~/stock-app

# 创建虚拟环境
python3.9 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境
cat > .env << EOF
DB_USER=stock_user
DB_PASS=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock
EOF

# 测试运行
streamlit run app.py
```

### 4. 配置服务

```bash
# 退出到root
exit

# 创建systemd服务
cat > /etc/systemd/system/stock-app.service << EOF
[Unit]
Description=Stock App
After=postgresql-14.service

[Service]
User=stockapp
WorkingDirectory=/home/stockapp/stock-app
Environment="PATH=/home/stockapp/stock-app/.venv/bin"
ExecStart=/home/stockapp/stock-app/.venv/bin/streamlit run app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl start stock-app
systemctl enable stock-app
```

---

## 🔧 常用命令

### 服务管理

```bash
# 查看状态
systemctl status stock-app

# 启动/停止/重启
systemctl start stock-app
systemctl stop stock-app
systemctl restart stock-app

# 查看日志
journalctl -u stock-app -f
```

### 数据库管理

```bash
# 连接数据库
sudo -u postgres psql stock

# 备份数据库
sudo -u postgres pg_dump stock > backup.sql

# 恢复数据库
sudo -u postgres psql stock < backup.sql

# 查看表
sudo -u postgres psql -d stock -c "\dt"
```

### 应用管理

```bash
# 进入应用目录
cd /home/stockapp/stock-app

# 激活虚拟环境
source .venv/bin/activate

# 更新代码（如果使用git）
git pull

# 重启服务
sudo systemctl restart stock-app

# 查看应用日志
tail -f logs/app.log
```

---

## ⚠️ 故障排查

### 应用无法启动

```bash
# 查看详细错误
systemctl status stock-app
journalctl -u stock-app -xe

# 检查端口占用
netstat -tulpn | grep 8502

# 手动测试
su - stockapp
cd ~/stock-app
source .venv/bin/activate
streamlit run app.py
```

### 数据库连接失败

```bash
# 检查PostgreSQL状态
systemctl status postgresql-14

# 测试连接
psql -h localhost -U stock_user -d stock

# 查看配置
vim /var/lib/pgsql/14/data/pg_hba.conf
vim /var/lib/pgsql/14/data/postgresql.conf
```

### 页面502错误

```bash
# 检查应用是否运行
ps aux | grep streamlit

# 检查端口监听
netstat -tulpn | grep 8502

# 重启应用
systemctl restart stock-app
```

---

## 🔒 安全建议

### 1. 修改数据库密码

```bash
sudo -u postgres psql
ALTER USER stock_user WITH PASSWORD 'new_strong_password';
\q

# 同时修改.env文件
vim /home/stockapp/stock-app/.env
```

### 2. 配置防火墙

```bash
# 仅允许特定IP访问
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="your-ip" port port="8502" protocol="tcp" accept'
firewall-cmd --reload
```

### 3. 使用Nginx反向代理

```bash
# 安装Nginx
yum install -y nginx

# 配置
cat > /etc/nginx/conf.d/stock.conf << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

# 启动Nginx
systemctl start nginx
systemctl enable nginx

# 开放80端口
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --reload
```

---

## 📦 备份与恢复

### 自动备份

```bash
# 创建备份脚本
cat > /usr/local/bin/backup-stock.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/stock"
DATE=$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# 备份数据库
sudo -u postgres pg_dump stock | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 备份应用配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /home/stockapp/stock-app/.env \
    /home/stockapp/stock-app/.streamlit

# 删除30天前的备份
find $BACKUP_DIR -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup-stock.sh

# 添加定时任务
crontab -e
# 添加：0 2 * * * /usr/local/bin/backup-stock.sh
```

### 手动备份

```bash
# 备份数据库
sudo -u postgres pg_dump stock > /backup/stock_$(date +%Y%m%d).sql

# 备份应用目录
tar -czf /backup/stock-app_$(date +%Y%m%d).tar.gz /home/stockapp/stock-app
```

### 恢复

```bash
# 恢复数据库
sudo -u postgres psql stock < /backup/stock_20240101.sql

# 恢复应用
tar -xzf /backup/stock-app_20240101.tar.gz -C /
systemctl restart stock-app
```

---

## 🔄 更新应用

### 使用Git更新

```bash
# 切换到应用用户
su - stockapp
cd ~/stock-app

# 停止服务
sudo systemctl stop stock-app

# 备份
cp .env .env.bak

# 更新代码
git pull

# 更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 启动服务
sudo systemctl start stock-app
```

### 手动更新

```bash
# 1. 备份当前版本
cd /home/stockapp
tar -czf stock-app-backup-$(date +%Y%m%d).tar.gz stock-app

# 2. 停止服务
systemctl stop stock-app

# 3. 上传新版本（覆盖旧文件）

# 4. 重新安装依赖
su - stockapp
cd ~/stock-app
source .venv/bin/activate
pip install -r requirements.txt

# 5. 启动服务
exit
systemctl start stock-app
```

---

## 📊 性能监控

### 系统资源

```bash
# 实时监控
htop

# 内存使用
free -h

# 磁盘使用
df -h

# 磁盘IO
iostat -x 1
```

### 应用监控

```bash
# 查看进程
ps aux | grep streamlit

# 查看端口
netstat -tulpn | grep 8502

# 查看连接数
ss -s
```

### 数据库监控

```bash
# 连接到数据库
sudo -u postgres psql stock

# 查看当前连接
SELECT * FROM pg_stat_activity;

# 查看数据库大小
SELECT pg_size_pretty(pg_database_size('stock'));

# 查看表大小
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 📞 获取帮助

- 查看完整文档：`/home/stockapp/stock-app/docs/`
- 查看部署日志：`/var/log/stock-deploy.log`
- 查看应用日志：`/home/stockapp/stock-app/logs/`
- 系统日志：`journalctl -u stock-app`

---

## ✅ 检查清单

部署完成后，请检查：

- [ ] PostgreSQL服务运行正常：`systemctl status postgresql-14`
- [ ] 数据库可以连接：`psql -h localhost -U stock_user -d stock`
- [ ] 应用服务运行正常：`systemctl status stock-app`
- [ ] 端口正常监听：`netstat -tulpn | grep 8502`
- [ ] 可以访问页面：`http://server-ip:8502`
- [ ] 日志没有错误：`tail -f /home/stockapp/stock-app/logs/app.log`
- [ ] 防火墙已配置：`firewall-cmd --list-ports`
- [ ] 自动备份已配置：`crontab -l`
- [ ] 服务开机自启：`systemctl is-enabled stock-app`

全部勾选后，部署完成！🎉
