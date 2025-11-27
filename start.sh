#!/bin/bash

# 股票量化交易系统启动脚本
# 用途：在服务器上安装依赖并后台运行Streamlit应用

# 设置日志文件路径
LOG_FILE="stock_app.log"
# 设置虚拟环境路径
VENV_PATH=".venv"
# 设置应用端口
PORT=8502

# 打印启动信息
echo "===== 股票量化交易系统启动脚本 ====="
echo "当前时间: $(date)"
echo "日志文件: $LOG_FILE"

# 检查并删除旧的日志文件
if [ -f "$LOG_FILE" ]; then
    echo "删除旧的日志文件..."
    rm -f "$LOG_FILE"
fi

# 检查并删除旧的虚拟环境
if [ -d "$VENV_PATH" ]; then
    echo "删除旧的虚拟环境..."
    rm -rf "$VENV_PATH"
fi

# 创建虚拟环境
echo "创建新的虚拟环境..."
python3 -m venv "$VENV_PATH"

# 激活虚拟环境
echo "激活虚拟环境..."
source "$VENV_PATH/bin/activate"

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装项目依赖..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "警告: 未找到.env文件，将创建默认配置"
    cat > .env << EOF
DB_USER=postgres
DB_PASS=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock
EOF
fi

# 检查.streamlit目录
if [ ! -d ".streamlit" ]; then
    echo "创建.streamlit目录..."
    mkdir -p .streamlit
fi

# 检查config.toml文件
if [ ! -f ".streamlit/config.toml" ]; then
    echo "创建默认的config.toml配置..."
    cat > .streamlit/config.toml << EOF
[server]
port = $PORT
enableCORS = false

[global]
hideDeprecationWarnings = true
hideWarningOnDirectExecution = true
EOF
fi

# 启动应用并将输出重定向到日志文件
echo "启动Streamlit应用，端口: $PORT..."
echo "使用以下命令查看日志: tail -f $LOG_FILE"
echo "===================================="

# 使用nohup在后台运行应用，重定向stdout和stderr到日志文件
nohup streamlit run app.py --server.port $PORT > "$LOG_FILE" 2>&1 &

# 获取进程ID
PID=$!
echo "应用已启动，进程ID: $PID"
echo "等待5秒后查看初始日志..."
sleep 5

# 显示初始日志
echo "\n初始日志内容:"
tail -n 20 "$LOG_FILE"

echo "\n启动完成！要停止应用，请使用: kill $PID"
echo "要实时查看日志，请使用: tail -f $LOG_FILE"