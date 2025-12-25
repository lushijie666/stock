# 股票量化交易系统 - 部署文档说明

本目录包含完整的 CentOS 服务器部署文档和工具。

## 📚 文档列表

### 1. 完整部署指南
**文件**: `deployment_guide_centos.md`

最详细的部署文档，包含：
- 系统要求和架构说明
- PostgreSQL 14 安装和配置
- Python 3.9 环境搭建
- 应用部署详细步骤
- Nginx 反向代理配置
- HTTPS 证书配置
- 安全加固措施
- 性能优化建议
- 完整的故障排查指南

**适用场景**：
- 首次部署
- 需要了解每个步骤细节
- 需要自定义配置

### 2. 快速参考手册
**文件**: `deployment_quick_reference.md`

精简的命令速查手册，包含：
- 3步快速部署流程
- 常用命令集合
- 故障排查速查
- 备份恢复指南
- 更新升级步骤

**适用场景**：
- 熟悉部署流程，需要快速查找命令
- 日常运维操作
- 应急故障处理

### 3. 一键部署脚本
**文件**: `../deploy-stock-app.sh`

自动化部署脚本，包含：
- 自动安装所有依赖
- 自动配置数据库
- 自动创建systemd服务
- 自动配置备份任务

**适用场景**：
- 快速部署新环境
- 批量部署多台服务器
- 标准化部署流程

---

## 🚀 使用方式

### 方式一：使用一键脚本（最简单）

```bash
# 1. 上传脚本到服务器
scp deploy-stock-app.sh root@server-ip:/root/

# 2. 上传应用代码
scp stock-app.tar.gz root@server-ip:/root/

# 3. 连接服务器
ssh root@server-ip

# 4. 解压应用
mkdir -p /home/stockapp/stock-app
tar -xzf stock-app.tar.gz -C /home/stockapp/stock-app/

# 5. 运行脚本
chmod +x deploy-stock-app.sh
./deploy-stock-app.sh
```

10-20分钟后，所有安装配置自动完成！

### 方式二：手动部署（可控性强）

按照 `deployment_guide_centos.md` 文档逐步操作：

1. 系统准备
2. 安装PostgreSQL 14
3. 安装Python 3.9
4. 部署应用
5. 配置服务

### 方式三：混合方式（推荐）

使用脚本安装基础环境，手动配置应用：

```bash
# 1. 编辑脚本，注释掉应用部署部分
vim deploy-stock-app.sh

# 2. 运行脚本安装环境
./deploy-stock-app.sh

# 3. 手动部署应用
# 按照文档中"步骤4: 部署应用"操作
```

---

## 📋 部署前准备

### 服务器要求

- **系统**: CentOS 7.x 或 8.x
- **CPU**: 2核以上
- **内存**: 2GB以上（推荐4GB）
- **硬盘**: 20GB以上
- **网络**: 能访问外网（用于下载软件包）

### 需要准备的信息

1. **服务器信息**
   - IP地址
   - SSH端口
   - root密码或SSH密钥

2. **数据库密码**
   - 在脚本或.env中设置
   - 建议使用强密码

3. **域名**（可选）
   - 如果需要配置域名访问
   - 如果需要HTTPS证书

4. **防火墙规则**
   - 需要开放的端口（默认8502）
   - 是否需要限制访问IP

### 本地需要准备

1. **项目代码**
   - 完整的项目文件
   - requirements.txt
   - .env.example（可选）

2. **部署脚本**
   - deploy-stock-app.sh

3. **上传工具**
   - SCP、SFTP或Git

---

## 🔍 部署后检查

部署完成后，请检查以下项目：

### 1. 服务状态检查

```bash
# PostgreSQL
systemctl status postgresql-14

# 应用服务
systemctl status stock-app

# Nginx（如果安装）
systemctl status nginx
```

### 2. 网络检查

```bash
# 检查端口监听
netstat -tulpn | grep 8502

# 测试本地访问
curl -I http://localhost:8502

# 检查防火墙
firewall-cmd --list-ports
```

### 3. 数据库检查

```bash
# 连接测试
psql -h localhost -U stock_user -d stock

# 查看表
\dt

# 退出
\q
```

### 4. 应用检查

```bash
# 查看日志
tail -f /home/stockapp/stock-app/logs/app.log

# 检查进程
ps aux | grep streamlit

# 访问测试
浏览器访问: http://server-ip:8502
```

---

## ⚠️ 常见问题

### 1. 脚本执行失败

**问题**: 脚本运行到中途报错退出

**解决**:
```bash
# 查看错误信息
cat /var/log/stock-deploy.log

# 根据错误信息排查，常见原因：
# - 网络问题：检查能否访问外网
# - 权限问题：确保使用root运行
# - 磁盘空间：df -h 检查空间
```

### 2. 数据库连接失败

**问题**: 应用无法连接数据库

**解决**:
```bash
# 1. 检查PostgreSQL状态
systemctl status postgresql-14

# 2. 检查认证配置
vim /var/lib/pgsql/14/data/pg_hba.conf
# 确保有: host all all 127.0.0.1/32 md5

# 3. 检查.env配置
cat /home/stockapp/stock-app/.env
# 确保密码正确

# 4. 手动测试连接
psql -h localhost -U stock_user -d stock
```

### 3. 应用无法访问

**问题**: 浏览器无法打开页面

**解决**:
```bash
# 1. 检查服务运行
systemctl status stock-app

# 2. 检查端口监听
netstat -tulpn | grep 8502

# 3. 检查防火墙
firewall-cmd --list-ports

# 4. 如果端口未开放
firewall-cmd --permanent --add-port=8502/tcp
firewall-cmd --reload

# 5. 检查应用日志
tail -f /home/stockapp/stock-app/logs/error.log
```

### 4. 依赖安装失败

**问题**: pip安装依赖报错

**解决**:
```bash
# 1. 确保已安装开发包
yum install -y gcc gcc-c++ postgresql14-devel

# 2. 升级pip
pip install --upgrade pip

# 3. 单独安装失败的包
pip install psycopg2-binary

# 4. 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 🔧 运维建议

### 1. 定期备份

```bash
# 自动备份已配置，确认定时任务
crontab -l

# 手动备份
sudo -u postgres pg_dump stock > backup.sql

# 备份到远程
scp backup.sql user@backup-server:/backup/
```

### 2. 日志清理

```bash
# 查看日志大小
du -sh /home/stockapp/stock-app/logs/

# 清理旧日志
find /home/stockapp/stock-app/logs/ -name "*.log" -mtime +30 -delete

# 配置日志轮转（已在部署文档中说明）
```

### 3. 性能监控

```bash
# 安装监控工具
yum install -y htop iotop

# 实时监控
htop

# 磁盘IO监控
iotop

# 网络监控
iftop
```

### 4. 安全更新

```bash
# 定期更新系统
yum update -y

# 配置自动安全更新
yum install -y yum-cron
systemctl enable yum-cron
systemctl start yum-cron
```

---

## 📞 获取支持

如果遇到问题：

1. **查看日志**
   - 应用日志：`/home/stockapp/stock-app/logs/`
   - 系统日志：`journalctl -u stock-app`
   - 数据库日志：`/var/lib/pgsql/14/data/log/`

2. **查阅文档**
   - 完整部署指南
   - 快速参考手册
   - 项目README

3. **联系技术支持**
   - GitHub Issues
   - 技术支持邮箱
   - 技术交流群

---

## 📝 文档更新

本文档持续更新，请关注版本变化：

- **版本**: 1.0.0
- **更新日期**: 2024-12-25
- **适用版本**: Stock App v1.0+
- **维护者**: Stock App Team

---

## ✅ 检查清单

部署前检查：
- [ ] 服务器满足最低配置要求
- [ ] 已准备好服务器登录信息
- [ ] 已设置数据库密码
- [ ] 已准备好项目代码
- [ ] 已下载部署脚本

部署中检查：
- [ ] 系统更新完成
- [ ] PostgreSQL安装成功
- [ ] Python环境配置完成
- [ ] 依赖安装无错误
- [ ] 数据库初始化成功

部署后检查：
- [ ] 所有服务正常运行
- [ ] 端口正常监听
- [ ] 可以访问应用
- [ ] 数据库连接正常
- [ ] 日志无错误
- [ ] 防火墙已配置
- [ ] 备份任务已设置
- [ ] 服务开机自启

全部完成，部署成功！🎉
