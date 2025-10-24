#!/usr/bin/env python3
"""
验证版本数据的完整性和一致性
详细检查每个版本的数据结构和内容
"""

import os
import pandas as pd
import json
import zipfile
import shutil
from datetime import datetime
import tempfile

class VersionDataVerifier:
    def __init__(self, archive_path="inference_max_pipeline/data_archive"):
        self.archive_path = archive_path
        self.versions = []

    def discover_versions(self):
        """发现所有可用的版本"""
        version_dirs = [d for d in os.listdir(self.archive_path)
                      if d.startswith('version_') and os.path.isdir(os.path.join(self.archive_path, d))]
        self.versions = sorted(version_dirs)
        print(f"发现 {len(self.versions)} 个版本:")
        for i, version in enumerate(self.versions):
            print(f"  {i+1}. {version}")

    def extract_zip_file(self, zip_path, extract_to=None):
        """解压zip文件并返回CSV文件路径"""
        if extract_to is None:
            extract_to = tempfile.mkdtemp()

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        # 查找解压后的CSV文件
        csv_files = [f for f in os.listdir(extract_to) if f.endswith('.csv')]
        if csv_files:
            return os.path.join(extract_to, csv_files[0])
        return None

    def load_version_data(self, version):
        """加载指定版本的数据"""
        version_path = os.path.join(self.archive_path, version)
        data = {}

        try:
            # 加载metadata
            with open(os.path.join(version_path, 'metadata.json'), 'r') as f:
                data['metadata'] = json.load(f)

            # 临时目录用于解压
            temp_dir_base = f"/tmp/{version}_extract"

            # 加载e2e数据
            e2e_zip = os.path.join(version_path, 'inference_max_e2e.zip.zip')
            if os.path.exists(e2e_zip):
                temp_dir = temp_dir_base + "_e2e"
                e2e_file = self.extract_zip_file(e2e_zip, temp_dir)
                if e2e_file:
                    data['e2e'] = pd.read_csv(e2e_file)

            # 加载interactivity数据
            inter_zip = os.path.join(version_path, 'inference_max_interactivity.zip.zip')
            if os.path.exists(inter_zip):
                temp_dir = temp_dir_base + "_inter"
                inter_file = self.extract_zip_file(inter_zip, temp_dir)
                if inter_file:
                    data['interactivity'] = pd.read_csv(inter_file)

            # 加载merged数据
            merged_zip = os.path.join(version_path, 'inference_max_merged.zip.zip')
            if os.path.exists(merged_zip):
                temp_dir = temp_dir_base + "_merged"
                merged_file = self.extract_zip_file(merged_zip, temp_dir)
                if merged_file:
                    data['merged'] = pd.read_csv(merged_file)

            # 清理临时文件
            for temp_dir in [temp_dir_base + "_e2e", temp_dir_base + "_inter", temp_dir_base + "_merged"]:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

            return data

        except Exception as e:
            print(f"加载版本 {version} 数据失败: {str(e)}")
            return None

    def analyze_version_data(self, version, data):
        """分析单个版本的数据"""
        analysis = {
            'version': version,
            'metadata': data['metadata'] if 'metadata' in data else None,
            'data_stats': {}
        }

        # 分析e2e数据
        if 'e2e' in data and data['e2e'] is not None:
            df = data['e2e']
            analysis['data_stats']['e2e'] = {
                'records': len(df),
                'columns': list(df.columns),
                'models': df['model_name'].unique().tolist() if 'model_name' in df.columns else [],
                'sequences': df['sequence_length'].unique().tolist() if 'sequence_length' in df.columns else [],
                'hw_keys': df['hwKey'].unique().tolist() if 'hwKey' in df.columns else [],
                'precisions': df['precision'].unique().tolist() if 'precision' in df.columns else [],
                'unique_combinations': len(df.groupby(['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp'])) if all(col in df.columns for col in ['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp']) else 0
            }

        # 分析interactivity数据
        if 'interactivity' in data and data['interactivity'] is not None:
            df = data['interactivity']
            analysis['data_stats']['interactivity'] = {
                'records': len(df),
                'columns': list(df.columns),
                'models': df['model_name'].unique().tolist() if 'model_name' in df.columns else [],
                'sequences': df['sequence_length'].unique().tolist() if 'sequence_length' in df.columns else [],
                'hw_keys': df['hwKey'].unique().tolist() if 'hwKey' in df.columns else [],
                'precisions': df['precision'].unique().tolist() if 'precision' in df.columns else [],
                'unique_combinations': len(df.groupby(['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp'])) if all(col in df.columns for col in ['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp']) else 0
            }

        # 分析merged数据
        if 'merged' in data and data['merged'] is not None:
            df = data['merged']
            analysis['data_stats']['merged'] = {
                'records': len(df),
                'columns': list(df.columns),
                'models': df['model_name'].unique().tolist() if 'model_name' in df.columns else [],
                'sequences': df['sequence_length'].unique().tolist() if 'sequence_length' in df.columns else [],
                'hw_keys': df['hwKey'].unique().tolist() if 'hwKey' in df.columns else [],
                'precisions': df['precision'].unique().tolist() if 'precision' in df.columns else [],
                'unique_combinations': len(df.groupby(['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp'])) if all(col in df.columns for col in ['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp']) else 0
            }

        return analysis

    def compare_versions(self, analysis1, analysis2):
        """比较两个版本的分析结果"""
        comparison = {
            'version1': analysis1['version'],
            'version2': analysis2['version'],
            'differences': {}
        }

        # 比较数据统计
        for data_type in ['e2e', 'interactivity', 'merged']:
            if data_type in analysis1['data_stats'] and data_type in analysis2['data_stats']:
                stats1 = analysis1['data_stats'][data_type]
                stats2 = analysis2['data_stats'][data_type]

                diff = {}

                # 比较记录数
                if stats1['records'] != stats2['records']:
                    diff['records'] = f"{stats1['records']} → {stats2['records']}"

                # 比较唯一组合数
                if stats1['unique_combinations'] != stats2['unique_combinations']:
                    diff['unique_combinations'] = f"{stats1['unique_combinations']} → {stats2['unique_combinations']}"

                # 比较模型列表
                if set(stats1['models']) != set(stats2['models']):
                    diff['models'] = {
                        'only_in_v1': list(set(stats1['models']) - set(stats2['models'])),
                        'only_in_v2': list(set(stats2['models']) - set(stats1['models']))
                    }

                # 比较序列长度列表
                if set(stats1['sequences']) != set(stats2['sequences']):
                    diff['sequences'] = {
                        'only_in_v1': list(set(stats1['sequences']) - set(stats2['sequences'])),
                        'only_in_v2': list(set(stats2['sequences']) - set(stats1['sequences']))
                    }

                # 比较硬件平台列表
                if set(stats1['hw_keys']) != set(stats2['hw_keys']):
                    diff['hw_keys'] = {
                        'only_in_v1': list(set(stats1['hw_keys']) - set(stats2['hw_keys'])),
                        'only_in_v2': list(set(stats2['hw_keys']) - set(stats1['hw_keys']))
                    }

                # 比较精度列表
                if set(stats1['precisions']) != set(stats2['precisions']):
                    diff['precisions'] = {
                        'only_in_v1': list(set(stats1['precisions']) - set(stats2['precisions'])),
                        'only_in_v2': list(set(stats2['precisions']) - set(stats1['precisions']))
                    }

                if diff:
                    comparison['differences'][data_type] = diff

        return comparison

    def run_full_analysis(self):
        """运行完整的版本数据验证"""
        print("🔍 开始详细的版本数据验证分析...")

        # 发现版本
        self.discover_versions()

        if len(self.versions) < 2:
            print("❌ 版本数量不足，无法进行对比分析")
            return

        # 分析每个版本
        all_analyses = []
        for version in self.versions:
            print(f"\n📊 分析版本: {version}")
            data = self.load_version_data(version)
            if data:
                analysis = self.analyze_version_data(version, data)
                all_analyses.append(analysis)

                # 打印基本统计
                for data_type in ['e2e', 'interactivity', 'merged']:
                    if data_type in analysis['data_stats']:
                        stats = analysis['data_stats'][data_type]
                        print(f"  {data_type}: {stats['records']} 条记录, {stats['unique_combinations']} 个唯一组合")

        # 比较版本
        print(f"\n🔍 比较版本间的差异...")
        for i in range(len(all_analyses) - 1):
            comparison = self.compare_versions(all_analyses[i], all_analyses[i + 1])
            print(f"\n📋 比较 {comparison['version1']} vs {comparison['version2']}:")

            if not comparison['differences']:
                print("  ✅ 无差异")
            else:
                for data_type, diff in comparison['differences'].items():
                    print(f"  🔹 {data_type} 数据差异:")
                    for key, value in diff.items():
                        print(f"    {key}: {value}")

        # 保存详细报告
        self.save_detailed_report(all_analyses)

    def save_detailed_report(self, analyses):
        """保存详细的分析报告"""
        output_dir = "version_data_verification"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print(f"\n💾 保存详细报告到 {output_dir}/")

        # 保存JSON格式的完整分析
        json_file = os.path.join(output_dir, f"detailed_version_analysis_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2)

        print(f"  📄 详细分析: {json_file}")

        # 生成Markdown格式的报告
        md_file = os.path.join(output_dir, f"version_analysis_report_{timestamp}.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# 版本数据验证分析报告\n\n")
            f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**分析版本数**: {len(self.versions)}\n\n")
            f.write(f"**版本列表**:\n")
            for version in self.versions:
                f.write(f"- {version}\n")
            f.write("\n")

            for analysis in analyses:
                f.write(f"## 版本: {analysis['version']}\n\n")

                if analysis['metadata']:
                    f.write(f"**抓取时间**: {analysis['metadata'].get('pipeline_start_time', 'N/A')}\n")
                    f.write(f"**管道ID**: {analysis['metadata'].get('pipeline_id', 'N/A')}\n\n")

                for data_type, stats in analysis['data_stats'].items():
                    f.write(f"### {data_type.upper()} 数据\n\n")
                    f.write(f"- **记录数**: {stats['records']}\n")
                    f.write(f"- **唯一组合数**: {stats['unique_combinations']}\n")
                    f.write(f"- **模型数量**: {len(stats['models'])}\n")
                    f.write(f"- **序列长度数量**: {len(stats['sequences'])}\n")
                    f.write(f"- **硬件平台数量**: {len(stats['hw_keys'])}\n")
                    f.write(f"- **精度类型数量**: {len(stats['precisions'])}\n\n")

        print(f"  📖 Markdown报告: {md_file}")
        return output_dir

def main():
    """主函数"""
    print("🚀 开始验证版本数据的完整性和一致性")

    verifier = VersionDataVerifier()
    verifier.run_full_analysis()

    print(f"\n✅ 验证完成！")

if __name__ == "__main__":
    main()