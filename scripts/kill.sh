#!/bin/bash

pids=$(ps aux | grep 'project_pactum' | grep -v grep | awk '{print $2}')

# 检查是否有找到进程
if [ -z "$pids" ]; then
    echo "not found 'project_pactum' process."
else
    # 循环终止每个PID对应的进程
    for pid in $pids; do
        echo "kill process PID: $pid"
        sudo kill -9 "$pid"
    done
fi