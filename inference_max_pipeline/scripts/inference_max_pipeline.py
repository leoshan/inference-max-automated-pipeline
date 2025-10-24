#!/usr/bin/env python3
"""
InferenceMAX 自动化数据管道
用于定期抓取、处理和合并 InferenceMAX 网站的AI推理性能数据
"""

import os
import sys
import yaml
import json
import shutil
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append('/root/semi-bench')

try:
    from api_scraper import scrape_api_data
    from clean_json_files import main as clean_main
    from convert_to_separated_csv import main as convert_main
    from join_csv_files import main as join_main
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all required scripts are in the correct location")
    sys.exit(1)

class InferenceMaxPipeline:
    """InferenceMAX 数据管道主类"""

    def __init__(self, config_file="config/pipeline_config.yaml"):
        """初始化数据管道"""
        self.start_time = datetime.now()
        self.pipeline_id = self.start_time.strftime("%Y%m%d_%H%M%S")

        self.config = self.load_config(config_file)
        self.setup_logging()
        self.setup_directories()

        self.logger.info(f"Pipeline {self.pipeline_id} initialized")
        self.logger.info(f"Configuration loaded from: {config_file}")

    def load_config(self, config_file):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / config_file

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def setup_logging(self):
        """设置日志系统"""
        log_config = self.config.get('logging', {})
        log_dir = Path(self.config['paths']['base_dir']) / self.config['paths']['log_dir']
        log_dir.mkdir(parents=True, exist_ok=True)

        # 创建日志文件名
        log_file = log_dir / f"pipeline_{self.pipeline_id}.log"

        # 配置日志
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger('InferenceMaxPipeline')

    def setup_directories(self):
        """创建必要的目录"""
        base_dir = Path(self.config['paths']['base_dir'])

        directories = [
            self.config['paths']['raw_data_dir'],
            self.config['paths']['output_dir'],
            self.config['paths']['archive_dir'],
            self.config['paths']['report_dir']
        ]

        for dir_path in directories:
            full_path = base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

    def log_step(self, step_name, message=""):
        """记录步骤日志"""
        self.logger.info(f"{'='*50}")
        self.logger.info(f"STEP: {step_name}")
        if message:
            self.logger.info(f"INFO: {message}")
        self.logger.info(f"{'='*50}")

    def scrape_data(self):
        """步骤1: 使用API直接采集数据"""
        self.log_step("数据采集", "开始从 InferenceMAX API 采集数据")

        try:
            # 临时修改工作目录到项目根目录
            original_cwd = os.getcwd()
            os.chdir(self.config['paths']['base_dir'])

            # 获取配置
            models = self.config['targets']['models']
            sequences = self.config['targets']['sequences']
            output_dir = self.config['paths']['raw_data_dir']

            self.logger.info(f"执行API数据采集...")
            self.logger.info(f"目标: {len(models)} 模型 × {len(sequences)} 序列")
            self.logger.info(f"输出目录: {output_dir}")

            # 执行API采集
            scrape_results = scrape_api_data(models, sequences, output_dir)

            # 恢复工作目录
            os.chdir(original_cwd)

            # 验证采集结果
            raw_data_dir = Path(self.config['paths']['base_dir']) / output_dir
            json_files = list(raw_data_dir.glob("*.json"))
            json_files = [f for f in json_files if not any(x in f.name.lower()
                       for x in ['readme', 'summary', 'cleanup', 'report', 'api_scraping_summary'])]

            self.logger.info(f"API采集完成，获得 {len(json_files)} 个JSON文件")
            self.logger.info(f"总记录数: {scrape_results.get('total_records', 0)}")
            self.logger.info(f"b200_trt数据: {scrape_results.get('total_b200_trt', 0)} 条")

            # 检查b200_trt数据
            if scrape_results.get('total_b200_trt', 0) == 0:
                self.logger.warning("未采集到任何b200_trt数据，可能需要检查网络或API端点")

            if len(json_files) < 6:  # 期望的最少文件数
                raise ValueError(f"采集的文件数量不足: {len(json_files)} < 6")

            return True

        except Exception as e:
            self.logger.error(f"数据爬取失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def clean_data(self):
        """步骤2: 清理无效数据"""
        self.log_step("数据清理", "移除无效和小文件")

        try:
            original_cwd = os.getcwd()
            os.chdir(self.config['paths']['base_dir'])

            self.logger.info("执行数据清理...")
            clean_main()

            os.chdir(original_cwd)

            # 验证清理结果
            raw_data_dir = Path(self.config['paths']['base_dir']) / self.config['paths']['raw_data_dir']
            valid_files = list(raw_data_dir.glob("*.json"))
            valid_files = [f for f in valid_files if not any(x in f.name.lower()
                          for x in ['readme', 'summary', 'cleanup', 'report'])]

            self.logger.info(f"清理完成，保留 {len(valid_files)} 个有效文件")

            return True

        except Exception as e:
            self.logger.error(f"数据清理失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def convert_to_csv(self):
        """步骤3: 转换为分离的CSV文件"""
        self.log_step("CSV转换", "将JSON数据转换为分离的CSV文件")

        try:
            original_cwd = os.getcwd()
            os.chdir(self.config['paths']['base_dir'])

            self.logger.info("执行CSV转换...")
            convert_main()

            os.chdir(original_cwd)

            # 验证转换结果
            output_dir = Path(self.config['paths']['base_dir']) / self.config['paths']['output_dir']
            interactivity_csv = output_dir / "inference_max_interactivity.csv"
            e2e_csv = output_dir / "inference_max_e2e.csv"

            if not interactivity_csv.exists() or not e2e_csv.exists():
                raise FileNotFoundError("CSV转换失败，缺少输出文件")

            # 检查文件大小
            inter_size = interactivity_csv.stat().st_size
            e2e_size = e2e_csv.stat().st_size

            self.logger.info(f"转换完成: Interactivity({inter_size:,} bytes), E2E({e2e_size:,} bytes)")

            return True

        except Exception as e:
            self.logger.error(f"CSV转换失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def join_csv_files(self):
        """步骤4: 合并CSV文件"""
        self.log_step("CSV合并", "将两个CSV文件合并为最终数据集")

        try:
            original_cwd = os.getcwd()
            os.chdir(self.config['paths']['base_dir'])

            self.logger.info("执行CSV合并...")
            join_main()

            os.chdir(original_cwd)

            # 验证合并结果
            output_dir = Path(self.config['paths']['base_dir']) / self.config['paths']['output_dir']
            merged_csv = output_dir / "inference_max_merged.csv"

            if not merged_csv.exists():
                raise FileNotFoundError("CSV合并失败，缺少输出文件")

            # 检查文件大小和记录数
            file_size = merged_csv.stat().st_size
            self.logger.info(f"合并完成: 最终文件大小 {file_size:,} bytes")

            # 验证数据完整性
            with open(merged_csv, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                record_count = len(lines) - 1  # 减去表头

            expected_min = self.config['monitoring'].get('expected_min_records', 1000)
            if record_count < expected_min:
                self.logger.warning(f"记录数可能不足: {record_count} < {expected_min}")
            else:
                self.logger.info(f"数据完整性验证通过: {record_count} 条记录")

            return True

        except Exception as e:
            self.logger.error(f"CSV合并失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def archive_version(self):
        """版本控制和归档"""
        if not self.config['versioning'].get('enabled', False):
            self.logger.info("版本控制已禁用，跳过归档")
            return True

        self.log_step("版本归档", "保存当前版本到历史档案")

        try:
            base_dir = Path(self.config['paths']['base_dir'])
            archive_dir = base_dir / self.config['paths']['archive_dir']
            output_dir = base_dir / self.config['paths']['output_dir']

            # 创建版本目录
            version_dir = archive_dir / f"version_{self.pipeline_id}"
            version_dir.mkdir(exist_ok=True)

            # 要归档的文件列表
            files_to_archive = [
                "inference_max_interactivity.csv",
                "inference_max_e2e.csv",
                "inference_max_merged.csv",
                "SEPARATED_CSV_CONVERSION_REPORT.md",
                "CSV_MERGE_REPORT.md"
            ]

            archived_files = []
            for file_name in files_to_archive:
                source_file = output_dir / file_name
                if source_file.exists():
                    target_file = version_dir / file_name
                    shutil.copy2(source_file, target_file)
                    archived_files.append(file_name)

                    # 如果启用压缩，压缩文件
                    if self.config['versioning'].get('compression', False):
                        shutil.make_archive(str(target_file.with_suffix('.zip')), 'zip', str(target_file.parent), target_file.name)
                        target_file.unlink()  # 删除原文件

                    self.logger.info(f"已归档: {file_name}")

            # 创建版本元数据
            version_metadata = {
                "pipeline_id": self.pipeline_id,
                "timestamp": self.start_time.isoformat(),
                "archived_files": archived_files,
                "config": self.config
            }

            metadata_file = version_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(version_metadata, f, indent=2, ensure_ascii=False)

            self.logger.info(f"版本归档完成: {version_dir}")

            # 清理旧版本
            self.cleanup_old_versions()

            return True

        except Exception as e:
            self.logger.error(f"版本归档失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def cleanup_old_versions(self):
        """清理旧版本"""
        max_versions = self.config['versioning'].get('max_versions', 30)
        archive_dir = Path(self.config['paths']['base_dir']) / self.config['paths']['archive_dir']

        version_dirs = [d for d in archive_dir.iterdir() if d.is_dir() and d.name.startswith('version_')]
        version_dirs.sort(reverse=True)  # 按时间倒序

        if len(version_dirs) > max_versions:
            for old_version in version_dirs[max_versions:]:
                try:
                    shutil.rmtree(old_version)
                    self.logger.info(f"已删除旧版本: {old_version.name}")
                except Exception as e:
                    self.logger.warning(f"删除旧版本失败 {old_version.name}: {e}")

    def create_final_report(self, success):
        """创建最终报告"""
        self.log_step("生成报告", f"创建管道执行报告 (成功: {success})")

        try:
            report_dir = Path(self.config['paths']['base_dir']) / self.config['paths']['report_dir']
            report_file = report_dir / f"pipeline_report_{self.pipeline_id}.md"

            end_time = datetime.now()
            duration = end_time - self.start_time

            report_content = f"""# InferenceMAX 数据管道执行报告

## 执行信息
- **管道ID**: {self.pipeline_id}
- **开始时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **结束时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **执行时长**: {str(duration).split('.')[0]}
- **执行状态**: {'✅ 成功' if success else '❌ 失败'}

## 配置信息
- **目标模型**: {', '.join(self.config['targets']['models'])}
- **目标序列**: {', '.join(self.config['targets']['sequences'])}
- **版本控制**: {'启用' if self.config['versioning']['enabled'] else '禁用'}

## 输出文件
"""

            if success:
                output_dir = Path(self.config['paths']['base_dir']) / self.config['paths']['output_dir']

                final_files = []
                for file_name in ["inference_max_interactivity.csv", "inference_max_e2e.csv", "inference_max_merged.csv"]:
                    file_path = output_dir / file_name
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        final_files.append(f"- **{file_name}**: {file_size:,} bytes")

                if final_files:
                    report_content += "### 生成的文件\n"
                    report_content += "\n".join(final_files) + "\n\n"

                if self.config['versioning']['enabled']:
                    report_content += f"### 版本归档\n"
                    report_content += f"- 版本目录: `version_{self.pipeline_id}`\n"
                    report_content += f"- 归档位置: `{self.config['paths']['archive_dir']}`\n\n"

            report_content += f"""
## 日志文件
- **详细日志**: `inference_max_pipeline/logs/pipeline_{self.pipeline_id}.log`

## 下次执行建议
- 检查数据质量是否符合预期
- 验证新数据与历史数据的趋势变化
- 关注数据更新频率和模式

---

*报告生成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}*
"""

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)

            self.logger.info(f"最终报告已生成: {report_file}")
            return True

        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)}")
            return False

    def run(self):
        """执行完整的管道流程"""
        self.logger.info(f"开始执行 InferenceMAX 数据管道 {self.pipeline_id}")

        success = False

        try:
            # 步骤1: 数据爬取
            if not self.scrape_data():
                return False

            # 步骤2: 数据清理
            if not self.clean_data():
                return False

            # 步骤3: CSV转换
            if not self.convert_to_csv():
                return False

            # 步骤4: CSV合并
            if not self.join_csv_files():
                return False

            # 步骤5: 版本归档
            if not self.archive_version():
                return False

            success = True
            self.logger.info("🎉 数据管道执行成功！")

        except Exception as e:
            self.logger.error(f"管道执行过程中发生异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            success = False

        finally:
            # 生成最终报告
            self.create_final_report(success)

            end_time = datetime.now()
            duration = end_time - self.start_time

            self.logger.info(f"管道执行完成")
            self.logger.info(f"总耗时: {str(duration).split('.')[0]}")
            self.logger.info(f"执行状态: {'✅ 成功' if success else '❌ 失败'}")

        return success

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='InferenceMAX 数据管道')
    parser.add_argument('--config', '-c', default='config/pipeline_config.yaml',
                       help='配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出')

    args = parser.parse_args()

    try:
        # 初始化管道
        pipeline = InferenceMaxPipeline(args.config)

        # 执行管道
        success = pipeline.run()

        # 设置退出码
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n管道执行被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"管道执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()