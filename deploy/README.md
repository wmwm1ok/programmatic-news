# 服务器部署指南

## 方案 1: 云服务器部署

### 1. 购买云服务器
推荐：AWS Lightsail / DigitalOcean / Vultr
- 配置：1核 2GB 内存
- 系统：Ubuntu 22.04 LTS
- 价格：约 $5-10/月

### 2. 连接到服务器
```bash
ssh root@你的服务器IP
```

### 3. 安装依赖
```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Python 和依赖
apt install -y python3 python3-pip python3-venv git

# 安装 Playwright 依赖
apt install -y libnss3 libatk-bridge2.0 libxss1 libgtk-3-0
```

### 4. 部署项目
```bash
# 克隆项目（或上传）
git clone <你的仓库地址> /opt/weekly-report
# 或手动上传项目文件

cd /opt/weekly-report

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 设置环境变量
export DEEPSEEK_API_KEY="your-api-key"
# 添加到 ~/.bashrc 使其永久生效
echo 'export DEEPSEEK_API_KEY="your-api-key"' >> ~/.bashrc
```

### 5. 测试运行
```bash
cd /opt/weekly-report
source venv/bin/activate
python3 generate_with_ai.py
```

### 6. 配置定时任务（每周一早上9点运行）
```bash
crontab -e

# 添加以下行
0 9 * * 1 cd /opt/weekly-report && /opt/weekly-report/venv/bin/python3 generate_with_ai.py >> /var/log/weekly-report.log 2>&1
```

---

## 方案 2: GitHub Actions（免费，推荐）

使用 GitHub 的免费 Action 服务，无需购买服务器。

### 1. 创建 GitHub 仓库
将项目代码推送到 GitHub 私有仓库

### 2. 配置 GitHub Secrets
在仓库 Settings -> Secrets and variables -> Actions 中添加：
- `DEEPSEEK_API_KEY`: your-api-key
- `EMAIL_USERNAME`: 你的邮箱
- `EMAIL_PASSWORD`: 邮箱密码

### 3. 启用 Actions
GitHub 会自动每周一早上9点运行

---

## 监控和日志

### 查看日志
```bash
tail -f /var/log/weekly-report.log
```
