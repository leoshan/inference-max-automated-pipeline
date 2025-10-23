#!/usr/bin/env python3
"""
InferenceMAX 数据管道调度器
用于定期自动执行数据抓取和处理任务
"""

import os
import sys
import yaml
import json
import time
import schedule
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append('/root/semi-bench')
sys.path.append('/root/semi-bench/inference_max_pipeline/scripts')

from inference_max_pipeline import InferenceMaxPipeline

class PipelineScheduler:
    """数据管道调度器"""

    def __init__(self, config_file="config/pipeline_config.yaml"):
        """初始化调度器"""
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.pipeline = None

        self.logger = logging.getLogger('PipelineScheduler')
        self.logger.info("Pipeline Scheduler initialized")

    def load_config(self, config_file):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / config_file
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def setup_logging(self):
        """设置日志系统"""
        log_config = self.config.get('logging', {})
        base_dir = Path(self.config['paths']['base_dir'])
        log_dir = base_dir / self.config['paths']['log_dir']

        log_dir.mkdir(parents=True, exist_ok=True)

        # 创建调度器专用日志
        log_file = log_dir / "scheduler.log"

        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def execute_pipeline(self):
        """执行数据管道"""
        try:
            self.logger.info("="*60)
            self.logger.info("开始执行定时数据管道")
            self.logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("="*60)

            # 初始化管道
            self.pipeline = InferenceMaxPipeline()

            # 执行管道
            success = self.pipeline.run()

            if success:
                self.logger.info("✅ 定时管道执行成功")
            else:
                self.logger.error("❌ 定时管道执行失败")

            return success

        except Exception as e:
            self.logger.error(f"定时管道执行异常: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def send_notification(self, success, error_message=""):
        """发送通知（如果配置了）"""
        try:
            notifications = self.config.get('notifications', {})

            # 这里可以添加邮件、webhook等通知方式
            if notifications.get('webhook', {}).get('enabled', False):
                self.send_webhook_notification(success, error_message)

            if notifications.get('email', {}).get('enabled', False):
                self.send_email_notification(success, error_message)

        except Exception as e:
            self.logger.error(f"发送通知失败: {e}")

    def send_webhook_notification(self, success, error_message):
        """发送Webhook通知"""
        import requests

        webhook_config = self.config['notifications']['webhook']
        url = webhook_config.get('url', '')

        if not url:
            return

        payload = {
            "timestamp": datetime.now().isoformat(),
            "pipeline_id": self.pipeline.pipeline_id if self.pipeline else "unknown",
            "success": success,
            "message": "InferenceMAX pipeline completed successfully" if success else f"Pipeline failed: {error_message}"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("Webhook通知发送成功")
            else:
                self.logger.warning(f"Webhook通知发送失败: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Webhook通知异常: {e}")

    def send_email_notification(self, success, error_message):
        """发送邮件通知"""
        # 这里可以实现邮件通知功能
        # 由于需要SMTP配置，这里只是示例
        self.logger.info("邮件通知功能暂未实现")

    def setup_schedule(self):
        """设置调度任务"""
        scheduling_config = self.config.get('scheduling', {})

        if not scheduling_config.get('enabled', False):
            self.logger.info("定时调度已禁用")
            return

        cron_expression = scheduling_config.get('cron_expression', '0 2 * * *')
        self.logger.info(f"设置定时任务: {cron_expression}")

        # 解析cron表达式并设置调度
        # 这里简化处理，实际应该使用croniter库
        if cron_expression == "0 2 * * *":  # 每天凌晨2点
            schedule.every().day.at("02:00").do(self.scheduled_execution)
        elif cron_expression == "0 */6 * * *":  # 每6小时
            schedule.every(6).hours.do(self.scheduled_execution)
        elif cron_expression == "0 0 * * 0":  # 每周日午夜
            schedule.every().sunday.at("00:00").do(self.scheduled_execution)
        else:
            # 默认每天凌晨2点
            schedule.every().day.at("02:00").do(self.scheduled_execution)

        self.logger.info("调度任务设置完成")

    def scheduled_execution(self):
        """定时执行的任务"""
        self.logger.info("开始执行定时任务")
        success = self.execute_pipeline()
        self.send_notification(success)
        return success

    def run_daemon(self):
        """以守护进程模式运行调度器"""
        self.logger.info("启动调度器守护进程")
        self.setup_schedule()

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            self.logger.info("调度器守护进程被用户中断")
        except Exception as e:
            self.logger.error(f"调度器守护进程异常: {e}")
            raise

    def run_once(self):
        """立即执行一次"""
        self.logger.info("执行一次性管道任务")
        return self.execute_pipeline()

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='InferenceMAX 数据管道调度器')
    parser.add_argument('--config', '-c', default='config/pipeline_config.yaml',
                       help='配置文件路径')
    parser.add_argument('--daemon', '-d', action='store_true',
                       help='以守护进程模式运行')
    parser.add_argument('--once', action='store_true',
                       help='立即执行一次')
    parser.add_argument('--test', action='store_true',
                       help='测试模式，只显示调度计划')

    args = parser.parse_args()

    try:
        scheduler = PipelineScheduler(args.config)

        if args.test:
            print("调度器测试模式")
            scheduler.setup_schedule()
            print("当前调度计划:")
            for job in schedule.jobs:
                print(f"  - {job}")
            return

        if args.once:
            success = scheduler.run_once()
            sys.exit(0 if success else 1)

        if args.daemon:
            scheduler.run_daemon()
        else:
            print("请指定运行模式: --daemon (守护进程) 或 --once (执行一次)")

    except KeyboardInterrupt:
        print("\n调度器被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"调度器运行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()