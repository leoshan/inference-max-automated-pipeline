# InferenceMAX 自动化数据管道系统总结

## 🎯 系统概述

基于前面完成的数据抓取和处理工作，我已经创建了一个完整的自动化数据管道系统，可以将整个流程固化并实现定期自动执行。

## 📊 原始流程回顾

我们之前完成了以下4个步骤：

1. **网页数据爬取** (`comprehensive_scraper.py`)
   - 从 InferenceMAX 网站爬取9个模型×序列组合的JSON数据
   - 每个组合4个JSON响应，共36个原始文件

2. **数据清理** (`clean_json_files.py`)
   - 移除无效的小文件（18个）
   - 保留18个高质量文件（1.3MB数据）

3. **CSV转换** (`convert_to_separated_csv.py`)
   - 将JSON转换为两个分离的CSV文件
   - `inference_max_interactivity.csv` - 交互式数据
   - `inference_max_e2e.csv` - 端到端数据

4. **数据合并** (`join_csv_files.py`)
   - 基于6个键字段进行join操作
   - 重命名x、y字段区分来源
   - 生成最终的合并CSV文件

## 🤖 自动化管道系统架构

### 核心组件

```
inference_max_pipeline/
├── config/
│   └── pipeline_config.yaml          # 配置管理
├── scripts/
│   ├── inference_max_pipeline.py    # 主管道控制脚本
│   ├── scheduler.py                  # 调度器
│   └── setup.py                      # 安装脚本
├── logs/                              # 执行日志
├── data_archive/                      # 历史版本归档
└── reports/                           # 执行报告
```

### 关键特性

1. **完整流程自动化**
   - 一键执行所有4个步骤
   - 自动错误处理和重试
   - 详细日志记录

2. **版本控制和归档**
   - 每次执行创建版本快照
   - 支持压缩存储
   - 可配置的版本保留策略

3. **调度和监控**
   - 支持定时自动执行
   - 系统服务集成
   - 通知机制（可选）

4. **配置化**
   - YAML配置文件
   - 灵活的参数调整
   - 环境适配

## 🚀 快速使用

### 1. 安装系统

```bash
cd /root/semi-bench
python inference_max_pipeline/scripts/setup.py
```

### 2. 快速启动（推荐）

```bash
# 交互式菜单启动
./run_pipeline.sh

# 或直接执行一次
python inference_max_pipeline/scripts/scheduler.py --once

# 或守护进程模式
python inference_max_pipeline/scripts/scheduler.py --daemon
```

### 3. 设置定时执行

#### systemd服务（推荐）
```bash
sudo systemctl enable inference-max-pipeline
sudo systemctl start inference-max-pipeline
```

#### crontab
```bash
crontab -e
# 添加：每天凌晨2点执行
0 2 * * * cd /root/semi-bench && python inference_max_pipeline/scripts/scheduler.py --once
```

## 📁 文件复用情况

### 可直接使用的原始文件
以下文件无需修改，直接在管道中使用：

1. **comprehensive_scraper.py** - 数据爬取脚本
2. **clean_json_files.py** - 数据清理脚本
3. **convert_to_separated_csv.py** - CSV转换脚本
4. **join_csv_files.py** - CSV合并脚本

### 新增的核心文件

1. **inference_max_pipeline.py** - 主控制脚本，整合所有步骤
2. **scheduler.py** - 调度器，支持定时执行
3. **pipeline_config.yaml** - 配置文件
4. **setup.py** - 安装和环境检查脚本
5. **run_pipeline.sh** - 快速启动菜单脚本

## 🔧 配置说明

### 主要配置项

```yaml
# 数据源配置
source:
  base_url: "https://inferencemax.semianalysis.com/"
  timeout: 600
  retry_attempts: 3

# 目标配置
targets:
  models: ["Llama 3.3 70B Instruct", "gpt-oss 120B", "DeepSeek R1 0528"]
  sequences: ["1K / 1K", "1K / 8K", "8K / 1K"]

# 调度配置
scheduling:
  enabled: true
  cron_expression: "0 2 * * *"  # 每天凌晨2点

# 版本控制
versioning:
  enabled: true
  max_versions: 30
  compression: true
```

## 📈 输出文件

### 主要输出
- `json_data/inference_max_merged.csv` - 最终合并的数据集
- `json_data/inference_max_interactivity.csv` - 交互式数据
- `json_data/inference_max_e2e.csv` - 端到端数据

### 历史归档
- `inference_max_pipeline/data_archive/version_YYYYMMDD_HHMMSS/` - 每次执行的完整快照

### 报告和日志
- `inference_max_pipeline/reports/` - 执行报告
- `inference_max_pipeline/logs/` - 详细日志

## 🛠️ 维护和监控

### 日常检查
```bash
# 查看最近执行状态
./run_pipeline.sh  # 选择选项4查看日志

# 检查服务状态
sudo systemctl status inference-max-pipeline

# 查看磁盘使用
du -sh inference_max_pipeline/
```

### 故障排除
```bash
# 查看详细日志
tail -f inference_max_pipeline/logs/pipeline_*.log

# 重新安装
python inference_max_pipeline/scripts/setup.py

# 测试管道
python inference_max_pipeline/scripts/scheduler.py --test
```

## 📋 执行流程详解

### 自动化流程图

```
开始
  ↓
[数据爬取] - comprehensive_scraper.py
  ↓
[数据清理] - clean_json_files.py
  ↓
[CSV转换] - convert_to_separated_csv.py
  ↓
[CSV合并] - join_csv_files.py
  ↓
[版本归档] - 保存历史版本
  ↓
[生成报告] - 执行摘要
  ↓
完成
```

### 错误处理
- 每个步骤都有独立的错误检测
- 失败时记录详细日志
- 支持自动重试机制
- 失败时发送通知（可选）

## 🎊 系统优势

1. **完全自动化** - 无需人工干预
2. **可靠稳定** - 错误处理和重试机制
3. **可配置** - 灵活的参数调整
4. **可追溯** - 完整的版本历史
5. **易维护** - 清晰的日志和报告
6. **可扩展** - 模块化设计，易于定制

## 📞 使用建议

### 首次使用
1. 运行安装脚本：`python inference_max_pipeline/scripts/setup.py`
2. 测试执行：`./run_pipeline.sh` 选择选项3测试
3. 执行一次：选择选项1验证完整流程
4. 设置定时任务：根据需要选择systemd或crontab

### 日常维护
- 定期检查日志文件
- 监控磁盘空间使用
- 根据需要调整调度频率
- 备份重要配置和数据

### 定制扩展
- 修改 `pipeline_config.yaml` 调整参数
- 在主管道脚本中添加新的处理步骤
- 扩展通知机制集成其他系统

---

## 🎉 总结

基于前面完成的数据抓取和处理工作，我成功创建了一个完整的自动化数据管道系统。这个系统固化了整个流程，实现了：

✅ **完全自动化** - 一键执行所有步骤
✅ **定期更新** - 支持定时自动执行
✅ **版本管理** - 完整的历史追溯
✅ **监控告警** - 实时状态监控
✅ **易于维护** - 清晰的文档和日志

现在您可以通过简单的命令就能定期获取最新的 InferenceMAX 数据，无需人工干预。系统会自动爬取、清理、转换和合并数据，并保存历史版本供分析使用。