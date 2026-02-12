#!/bin/bash
# 部署脚本 - 在服务器上运行

set -e

echo "=== 周报系统部署脚本 ==="

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行"
    exit 1
fi

# 安装系统依赖
echo "[1/5] 安装系统依赖..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git cron
apt-get install -y libnss3 libatk-bridge2.0-0 libxss1 libgtk-3-0

# 创建应用目录
echo "[2/5] 创建应用目录..."
mkdir -p /opt/weekly-report
cd /opt/weekly-report

# 复制项目文件（假设已通过 scp 上传）
echo "[3/5] 检查项目文件..."
if [ ! -f "requirements.txt" ]; then
    echo "错误：未找到项目文件，请先将项目上传到 /opt/weekly-report"
    exit 1
fi

# 创建虚拟环境并安装依赖
echo "[4/5] 安装 Python 依赖..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 安装 Playwright 浏览器
echo "安装 Playwright 浏览器..."
playwright install chromium

# 设置环境变量
echo "[5/5] 配置环境变量..."
if ! grep -q "DEEPSEEK_API_KEY" /etc/environment; then
    echo "请输入 DeepSeek API Key:"
    read -s API_KEY
    echo "DEEPSEEK_API_KEY=$API_KEY" >> /etc/environment
    echo "DEEPSEEK_API_BASE=https://api.deepseek.com" >> /etc/environment
    echo "DEEPSEEK_MODEL=deepseek-chat" >> /etc/environment
fi

# 配置定时任务
echo "配置定时任务..."
CRON_JOB="0 9 * * 1 cd /opt/weekly-report && /opt/weekly-report/venv/bin/python3 generate_with_ai.py >> /var/log/weekly-report.log 2>&1"

if ! (crontab -l 2>/dev/null | grep -q "weekly-report"); then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "定时任务已添加"
else
    echo "定时任务已存在"
fi

# 创建日志文件
touch /var/log/weekly-report.log
chmod 666 /var/log/weekly-report.log

echo ""
echo "=== 部署完成 ==="
echo "应用目录: /opt/weekly-report"
echo "日志文件: /var/log/weekly-report.log"
echo ""
echo "测试运行命令:"
echo "  cd /opt/weekly-report && source venv/bin/activate && python3 generate_with_ai.py"
echo ""
echo "查看日志:"
echo "  tail -f /var/log/weekly-report.log"
