#!/bin/bash

# InferenceMAX 数据管道快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} InferenceMAX 数据管道快速启动${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 检查依赖
check_dependencies() {
    print_message "检查系统依赖..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi

    # 检查ChromeDriver
    if ! command -v chromedriver &> /dev/null; then
        print_warning "ChromeDriver 未找到，请手动安装"
        echo "安装方法："
        echo "1. 下载: https://chromedriver.chromium.org/"
        echo "2. 解压到 /usr/local/bin/chromedriver"
        echo "3. 添加执行权限: chmod +x /usr/local/bin/chromedriver"
    else
        print_message "ChromeDriver 已安装: $(chromedriver --version)"
    fi

    # 检查目录
    if [ ! -d "inference_max_pipeline" ]; then
        print_error "inference_max_pipeline 目录不存在"
        exit 1
    fi
}

# 显示菜单
show_menu() {
    echo ""
    echo "请选择操作："
    echo "1) 执行一次完整的数据管道"
    echo "2) 以守护进程模式运行"
    echo "3) 测试管道"
    echo "4) 查看最近的日志"
    echo "5) 查看配置文件"
    echo "6) 安装/更新系统"
    echo "7) 退出"
    echo ""
    read -p "请输入选项 (1-7): " choice
}

# 执行管道
run_pipeline() {
    print_message "开始执行数据管道..."
    cd /root/semi-bench

    python3 inference_max_pipeline/scripts/scheduler.py --once

    if [ $? -eq 0 ]; then
        print_message "管道执行成功！"
        echo ""
        echo "输出文件："
        ls -la json_data/inference_max_*.csv
        echo ""
        echo "执行报告："
        ls -la inference_max_pipeline/reports/ | tail -3
    else
        print_error "管道执行失败，请查看日志"
        echo "最新日志："
        ls -la inference_max_pipeline/logs/ | tail -1
    fi
}

# 守护进程模式
run_daemon() {
    print_message "启动守护进程模式..."
    cd /root/semi-bench

    # 检查是否已有进程在运行
    if pgrep -f "scheduler.py.*--daemon" > /dev/null; then
        print_warning "调度器守护进程已在运行"
        echo "PID: $(pgrep -f 'scheduler.py.*--daemon')"
        read -p "是否停止现有进程? (y/n): " stop_choice
        if [ "$stop_choice" = "y" ]; then
            pkill -f "scheduler.py.*--daemon"
            print_message "已停止现有进程"
        fi
    fi

    print_message "启动新的守护进程..."
    nohup python3 inference_max_pipeline/scripts/scheduler.py --daemon > inference_max_pipeline/logs/daemon.log 2>&1 &

    sleep 2
    if pgrep -f "scheduler.py.*--daemon" > /dev/null; then
        print_message "守护进程启动成功！"
        echo "PID: $(pgrep -f 'scheduler.py.*--daemon')"
        echo "日志文件: inference_max_pipeline/logs/daemon.log"
        echo ""
        echo "使用以下命令管理守护进程："
        echo "  停止: pkill -f 'scheduler.py.*--daemon'"
        echo "  查看日志: tail -f inference_max_pipeline/logs/daemon.log"
    else
        print_error "守护进程启动失败"
    fi
}

# 测试管道
test_pipeline() {
    print_message "测试管道配置..."
    cd /root/semi-bench

    python3 inference_max_pipeline/scripts/scheduler.py --test
}

# 查看日志
show_logs() {
    echo ""
    echo "最近的日志文件："
    ls -la inference_max_pipeline/logs/ | tail -5

    echo ""
    read -p "输入要查看的日志文件名 (或按回车查看最新): " log_file

    if [ -z "$log_file" ]; then
        # 查看最新的日志
        latest_log=$(ls -t inference_max_pipeline/logs/pipeline_*.log 2>/dev/null | head -1)
        if [ -n "$latest_log" ]; then
            print_message "查看最新日志: $latest_log"
            tail -20 "$latest_log"
        else
            print_warning "没有找到管道日志文件"
        fi
    else
        if [ -f "inference_max_pipeline/logs/$log_file" ]; then
            print_message "查看日志: $log_file"
            tail -20 "inference_max_pipeline/logs/$log_file"
        else
            print_error "日志文件不存在: $log_file"
        fi
    fi
}

# 查看配置
show_config() {
    config_file="inference_max_pipeline/config/pipeline_config.yaml"

    if [ -f "$config_file" ]; then
        print_message "配置文件: $config_file"
        echo ""
        cat "$config_file"
    else
        print_error "配置文件不存在"
    fi
}

# 安装系统
install_system() {
    print_message "开始安装/更新系统..."
    cd /root/semi-bench

    python3 inference_max_pipeline/scripts/setup.py

    if [ $? -eq 0 ]; then
        print_message "安装/更新完成！"
        echo ""
        echo "下一步："
        echo "1. 测试管道: 选项 3"
        echo "2. 执行一次: 选项 1"
        echo "3. 设置定时任务"
    else
        print_error "安装失败"
    fi
}

# 主函数
main() {
    print_header
    check_dependencies

    while true; do
        show_menu

        case $choice in
            1)
                run_pipeline
                ;;
            2)
                run_daemon
                ;;
            3)
                test_pipeline
                ;;
            4)
                show_logs
                ;;
            5)
                show_config
                ;;
            6)
                install_system
                ;;
            7)
                print_message "退出"
                exit 0
                ;;
            *)
                print_error "无效选项，请重新选择"
                ;;
        esac

        echo ""
        read -p "按回车键继续..."
    done
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # 如果直接运行脚本，显示菜单
    main
fi