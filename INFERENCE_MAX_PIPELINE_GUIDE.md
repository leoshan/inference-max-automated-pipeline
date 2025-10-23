# InferenceMAX 自动化数据管道使用指南

## 📋 概述

本指南介绍如何使用 InferenceMAX 自动化数据管道系统，该系统可以定期自动抓取、处理和合并 InferenceMAX 网站的AI推理性能数据。

### 🔄 完整流程

1. **网页数据爬取** - 从 https://inferencemax.semianalysis.com/ 自动爬取JSON数据
2. **数据清理** - 移除无效和小文件，确保数据质量
3. **CSV转换** - 将JSON数据转换为分离的interactivity和e2e CSV文件
4. **数据合并** - 基于多键将两个CSV文件合并为最终数据集
5. **版本归档** - 保存历史版本，支持数据追溯
6. **自动调度** - 支持定时自动执行

## 🚀 快速开始

### 1. 安装和设置

```bash
# 运行安装脚本
cd /root/semi-bench
python inference_max_pipeline/scripts/setup.py
```

安装脚本会自动：
- 检查Python版本和依赖
- 安装必要的Python包
- 创建目录结构
- 设置文件权限
- 提供systemd服务和crontab配置

### 2. 手动执行一次

```bash
# 执行一次完整的数据管道
python inference_max_pipeline/scripts/scheduler.py --once
```

### 3. 设置定时执行

#### 方法一: 使用systemd服务 (推荐)

```bash
# 启用systemd服务
sudo systemctl daemon-reload
sudo systemctl enable inference-max-pipeline
sudo systemctl start inference-max-pipeline

# 查看服务状态
sudo systemctl status inference-max-pipeline

# 查看日志
sudo journalctl -u inference-max-pipeline -f
```

#### 方法二: 使用crontab

```bash
# 编辑crontab
crontab -e

# 添加以下行（每天凌晨2点执行）
0 2 * * * cd /root/semi-bench && python inference_max_pipeline/scripts/scheduler.py --once >> inference_max_pipeline/logs/cron.log 2>&1
```

## 📁 目录结构

```
inference_max_pipeline/
├── config/
│   └── pipeline_config.yaml          # 主配置文件
├── logs/
│   ├── pipeline_YYYYMMDD_HHMMSS.log  # 每次执行的详细日志
│   └── scheduler.log                  # 调度器日志
├── data_archive/
│   └── version_YYYYMMDD_HHMMSS/     # 历史版本归档
├── reports/
│   └── pipeline_report_YYYYMMDD_HHMMSS.md  # 执行报告
└── scripts/
    ├── inference_max_pipeline.py    # 主管道脚本
    ├── scheduler.py                  # 调度器脚本
    └── setup.py                      # 安装脚本
```

## ⚙️ 配置说明

### 主配置文件: `inference_max_pipeline/config/pipeline_config.yaml`

#### 数据源配置
```yaml
source:
  base_url: "https://inferencemax.semianalysis.com/"
  timeout: 600
  retry_attempts: 3
  retry_delay: 5
```

#### 目标配置
```yaml
targets:
  models:
    - "Llama 3.3 70B Instruct"
    - "gpt-oss 120B"
    - "DeepSeek R1 0528"
  sequences:
    - "1K / 1K"
    - "1K / 8K"
    - "8K / 1K"
```

#### 调度配置
```yaml
scheduling:
  enabled: true
  cron_expression: "0 2 * * *"  # 每天凌晨2点
  timezone: "UTC"
```

#### 版本控制
```yaml
versioning:
  enabled: true
  max_versions: 30
  compression: true
  date_format: "%Y%m%d_%H%M%S"
```

## 🔧 使用方法

### 基本命令

```bash
# 查看帮助
python inference_max_pipeline/scripts/scheduler.py --help

# 执行一次完整管道
python inference_max_pipeline/scripts/scheduler.py --once

# 以守护进程模式运行
python inference_max_pipeline/scripts/scheduler.py --daemon

# 测试调度配置
python inference_max_pipeline/scripts/scheduler.py --test

# 使用自定义配置文件
python inference_max_pipeline/scripts/scheduler.py --config custom_config.yaml
```

### 单独执行各个步骤

如果需要单独执行某个步骤，可以直接运行对应的脚本：

```bash
# 1. 数据爬取
python comprehensive_scraper.py

# 2. 数据清理
python clean_json_files.py

# 3. CSV转换
python convert_to_separated_csv.py

# 4. CSV合并
python join_csv_files.py
```

## 📊 输出文件

### 主要输出文件

1. **json_data/inference_max_merged.csv** - 最终合并的数据集
2. **json_data/inference_max_interactivity.csv** - 交互式性能数据
3. **json_data/inference_max_e2e.csv** - 端到端性能数据

### 历史归档

- **inference_max_pipeline/data_archive/** - 历史版本数据
- 每次执行都会创建一个新的版本目录
- 支持压缩存储以节省空间

### 报告和日志

- **inference_max_pipeline/reports/** - 执行报告
- **inference_max_pipeline/logs/** - 详细日志

## 🔍 监控和故障排除

### 查看执行状态

```bash
# 查看最新的执行日志
ls -la inference_max_pipeline/logs/ | tail -5
tail -f inference_max_pipeline/logs/pipeline_$(date +%Y%m%d)*.log

# 查看执行报告
ls -la inference_max_pipeline/reports/ | tail -5
cat inference_max_pipeline/reports/pipeline_report_$(date +%Y%m%d)*.md
```

### 常见问题

#### 1. ChromeDriver 问题
```bash
# 检查ChromeDriver
chromedriver --version

# 重新安装ChromeDriver
wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/LATEST_RELEASE/chromedriver_linux64.zip
cd /tmp && unzip chromedriver.zip && sudo mv chromedriver /usr/local/bin/ && sudo chmod +x /usr/local/bin/chromedriver
```

#### 2. 权限问题
```bash
# 设置执行权限
chmod +x inference_max_pipeline/scripts/*.py
chmod +x json_data/raw_json_files/*.json
```

#### 3. 内存不足
```bash
# 监控内存使用
free -h

# 如果内存不足，可以考虑：
# 1. 增加swap空间
# 2. 调整Chrome选项减少内存使用
# 3. 使用更轻量级的浏览器
```

#### 4. 网络问题
```bash
# 测试网络连接
curl -I https://inferencemax.semianalysis.com/

# 如果网络超时，在配置文件中增加timeout值
```

### 数据质量检查

```bash
# 检查最终CSV文件
wc -l json_data/inference_max_merged.csv
head -5 json_data/inference_max_merged.csv

# 检查数据分布
cut -d',' -f1 json_data/inference_max_merged.csv | sort | uniq -c
```

## 📈 高级配置

### 自定义调度

```yaml
scheduling:
  enabled: true
  cron_expression: "0 */6 * * *"  # 每6小时
  # 或者
  cron_expression: "0 0 * * 0"     # 每周日
```

### 通知配置

```yaml
notifications:
  webhook:
    enabled: true
    url: "https://hooks.slack.com/services/..."

  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your-email@gmail.com"
    password: "your-app-password"
    recipients: ["admin@example.com"]
```

### 性能调优

```yaml
performance:
  max_concurrent_downloads: 3
  request_timeout: 30
  page_load_timeout: 10
```

## 📋 维护建议

### 定期维护任务

1. **每周检查**
   - 查看执行日志
   - 验证数据质量
   - 检查磁盘空间

2. **每月维护**
   - 清理旧版本（如果需要）
   - 更新依赖包
   - 备份重要数据

3. **故障响应**
   - 监控日志错误
   - 检查数据完整性
   - 验证输出文件

### 备份策略

```bash
# 备份配置文件
tar -czf inference_max_pipeline_backup_$(date +%Y%m%d).tar.gz \
    inference_max_pipeline/config/ \
    inference_max_pipeline/scripts/

# 备份重要数据
tar -czf inference_max_data_backup_$(date +%Y%m%d).tar.gz \
    json_data/inference_max_*.csv \
    inference_max_pipeline/reports/ \
    inference_max_pipeline/logs/
```

## 🛠️ 扩展和定制

### 添加新的数据处理步骤

1. 在 `inference_max_pipeline/scripts/` 中创建新的脚本
2. 在 `inference_max_pipeline.py` 中添加新的步骤函数
3. 更新配置文件以支持新的参数

### 集成其他数据源

1. 修改配置文件添加新的数据源配置
2. 创建对应的爬取脚本
3. 在主管道中集成新的数据流

### 自定义数据处理

1. 修改 `convert_to_separated_csv.py` 改变CSV转换逻辑
2. 修改 `join_csv_files.py` 改变合并策略
3. 添加数据验证和清洗规则

## 📞 技术支持

### 日志分析

```bash
# 查看错误日志
grep "ERROR" inference_max_pipeline/logs/pipeline_*.log

# 查看性能统计
grep "完成" inference_max_pipeline/logs/pipeline_*.log

# 分析执行时间
grep "执行时长" inference_max_pipeline/reports/pipeline_report_*.md
```

### 性能监控

```bash
# 监控系统资源
top -p $(pgrep -f inference_max_pipeline)

# 监控磁盘使用
du -sh inference_max_pipeline/
df -h
```

---

*本指南涵盖了 InferenceMAX 数据管道的完整使用方法。如有其他问题，请查看日志文件或联系技术支持。*