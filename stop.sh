#!/bin/bash

# 股票量化交易系统停止脚本
# 用途：停止后台运行的Streamlit应用

echo "===== 股票量化交易系统停止脚本 ====="
echo "当前时间: $(date)"

# 查找Streamlit应用进程
PID=$(ps aux | grep "streamlit run app.py" | grep -v grep | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "没有找到运行中的Streamlit应用进程"
    exit 0
fi

echo "找到Streamlit应用进程，进程ID: $PID"

# 终止进程
echo "正在停止进程..."
kill $PID

# 检查进程是否成功终止
sleep 2
if ps -p $PID > /dev/null; then
    echo "警告: 进程未能正常终止，正在强制终止..."
    kill -9 $PID
    if ps -p $PID > /dev/null; then
        echo "错误: 无法终止进程，请手动处理"
        exit 1
    else
        echo "进程已强制终止"
    fi
else
    echo "进程已成功终止"
fi

echo "停止完成！"