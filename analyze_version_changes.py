#!/usr/bin/env python3
"""
分析不同版本间的数据变化差异
对比 e2e、interactivity 和 merged 数据的变化
"""

import os
import pandas as pd
import json
import zipfile
from datetime import datetime
import shutil

class VersionChangeAnalyzer:
    def __init__(self, archive_path="inference_max_pipeline/data_archive"):
        self.archive_path = archive_path
        self.versions = []
        self.data_cache = {}

    def discover_versions(self):
        """发现所有可用的版本"""
        version_dirs = [d for d in os.listdir(self.archive_path)
                      if d.startswith('version_') and os.path.isdir(os.path.join(self.archive_path, d))]
        self.versions = sorted(version_dirs)
        print(f"发现 {len(self.versions)} 个版本:")
        for i, version in enumerate(self.versions):
            print(f"  {i+1}. {version}")

    def extract_zip_file(self, zip_path, extract_to=None):
        """解压zip文件"""
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
        if version in self.data_cache:
            return self.data_cache[version]

        version_path = os.path.join(self.archive_path, version)
        data = {}

        try:
            # 加载metadata
            with open(os.path.join(version_path, 'metadata.json'), 'r') as f:
                data['metadata'] = json.load(f)

            # 临时目录用于解压
            temp_dir = f"/tmp/{version}_extract"
            os.makedirs(temp_dir, exist_ok=True)

            # 加载e2e数据
            e2e_zip = os.path.join(version_path, 'inference_max_e2e.zip.zip')
            e2e_file = self.extract_zip_file(e2e_zip, temp_dir + "_e2e")
            if e2e_file:
                data['e2e'] = pd.read_csv(e2e_file)

            # 加载interactivity数据
            inter_zip = os.path.join(version_path, 'inference_max_interactivity.zip.zip')
            inter_file = self.extract_zip_file(inter_zip, temp_dir + "_inter")
            if inter_file:
                data['interactivity'] = pd.read_csv(inter_file)

            # 加载merged数据
            merged_zip = os.path.join(version_path, 'inference_max_merged.zip.zip')
            merged_file = self.extract_zip_file(merged_zip, temp_dir + "_merged")
            if merged_file:
                data['merged'] = pd.read_csv(merged_file)

            self.data_cache[version] = data

            # 清理临时文件
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            return data

        except Exception as e:
            print(f"加载版本 {version} 数据失败: {str(e)}")
            return None

    def compare_dataframes(self, df1, df2, key_columns, value_columns, df1_name, df2_name):
        """比较两个DataFrame的差异"""
        if df1 is None or df2 is None:
            return pd.DataFrame()

        # 确保列名一致
        all_columns = list(set(df1.columns) | set(df2.columns))
        for col in all_columns:
            if col not in df1.columns:
                df1[col] = None
            if col not in df2.columns:
                df2[col] = None

        # 使用外连接找差异
        merged = pd.merge(df1, df2, on=key_columns, how='outer', suffixes=(f'_{df1_name}', f'_{df2_name}'))

        differences = []

        for idx, row in merged.iterrows():
            change_info = {col: row[col] for col in key_columns}

            has_change = False

            for val_col in value_columns:
                col1 = f"{val_col}_{df1_name}"
                col2 = f"{val_col}_{df2_name}"

                val1 = row[col1]
                val2 = row[col2]

                if pd.isna(val1) and pd.isna(val2):
                    continue
                elif pd.isna(val1):
                    change_info[f"{val_col}_change"] = f"新增: {val2}"
                    has_change = True
                elif pd.isna(val2):
                    change_info[f"{val_col}_change"] = f"删除: {val1}"
                    has_change = True
                elif val1 != val2:
                    change_info[f"{val_col}_change"] = f"{val1} → {val2}"
                    change_info[f"{val_col}_diff"] = val2 - val1
                    change_info[f"{val_col}_diff_percent"] = ((val2 - val1) / val1 * 100) if val1 != 0 else None
                    has_change = True

            if has_change:
                differences.append(change_info)

        return pd.DataFrame(differences)

    def analyze_all_changes(self):
        """分析所有版本间的变化"""
        if len(self.versions) < 2:
            print("需要至少两个版本才能分析变化")
            return

        print(f"\n🔍 开始分析 {len(self.versions)} 个版本间的数据变化...")

        # 定义比较的关键列
        key_columns = ['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp']

        results = {
            'e2e_changes': [],
            'interactivity_changes': [],
            'merged_changes': []
        }

        for i in range(len(self.versions) - 1):
            version1 = self.versions[i]
            version2 = self.versions[i + 1]

            print(f"\n📊 比较版本 {version1} vs {version2}")

            # 加载数据
            data1 = self.load_version_data(version1)
            data2 = self.load_version_data(version2)

            if not data1 or not data2:
                print(f"❌ 无法加载数据，跳过比较")
                continue

            # 比较e2e数据
            print("  🔹 分析e2e数据变化...")
            e2e_diff = self.compare_dataframes(
                data1['e2e'], data2['e2e'],
                key_columns, ['x', 'y'],
                'v1', 'v2'
            )
            if not e2e_diff.empty:
                e2e_diff['comparison'] = f"{version1}_vs_{version2}"
                results['e2e_changes'].append(e2e_diff)
                print(f"    发现 {len(e2e_diff)} 个变化")
            else:
                print("    无变化")

            # 比较interactivity数据
            print("  🔹 分析interactivity数据变化...")
            inter_diff = self.compare_dataframes(
                data1['interactivity'], data2['interactivity'],
                key_columns, ['x', 'y'],
                'v1', 'v2'
            )
            if not inter_diff.empty:
                inter_diff['comparison'] = f"{version1}_vs_{version2}"
                results['interactivity_changes'].append(inter_diff)
                print(f"    发现 {len(inter_diff)} 个变化")
            else:
                print("    无变化")

            # 比较merged数据
            print("  🔹 分析merged数据变化...")
            merged_diff = self.compare_dataframes(
                data1['merged'], data2['merged'],
                key_columns, ['e2e_x', 'e2e_y', 'inter_x', 'inter_y'],
                'v1', 'v2'
            )
            if not merged_diff.empty:
                merged_diff['comparison'] = f"{version1}_vs_{version2}"
                results['merged_changes'].append(merged_diff)
                print(f"    发现 {len(merged_diff)} 个变化")
            else:
                print("    无变化")

        return results

    def save_results(self, results, output_dir="version_change_analysis"):
        """保存分析结果"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print(f"\n💾 保存分析结果到 {output_dir}/")

        # 保存e2e变化
        if results['e2e_changes']:
            e2e_all = pd.concat(results['e2e_changes'], ignore_index=True)
            e2e_file = os.path.join(output_dir, f"e2e_data_changes_{timestamp}.csv")
            e2e_all.to_csv(e2e_file, index=False, encoding='utf-8')
            print(f"  📄 E2E数据变化: {e2e_file} ({len(e2e_all)} 条记录)")

        # 保存interactivity变化
        if results['interactivity_changes']:
            inter_all = pd.concat(results['interactivity_changes'], ignore_index=True)
            inter_file = os.path.join(output_dir, f"interactivity_data_changes_{timestamp}.csv")
            inter_all.to_csv(inter_file, index=False, encoding='utf-8')
            print(f"  📄 Interactivity数据变化: {inter_file} ({len(inter_all)} 条记录)")

        # 保存merged变化
        if results['merged_changes']:
            merged_all = pd.concat(results['merged_changes'], ignore_index=True)
            merged_file = os.path.join(output_dir, f"merged_data_changes_{timestamp}.csv")
            merged_all.to_csv(merged_file, index=False, encoding='utf-8')
            print(f"  📄 Merged数据变化: {merged_file} ({len(merged_all)} 条记录)")

        # 生成摘要报告
        summary = {
            "analysis_time": datetime.now().isoformat(),
            "versions_analyzed": self.versions,
            "changes_found": {
                "e2e": len(results['e2e_changes']) * len(results['e2e_changes'][0]) if results['e2e_changes'] else 0,
                "interactivity": len(results['interactivity_changes']) * len(results['interactivity_changes'][0]) if results['interactivity_changes'] else 0,
                "merged": len(results['merged_changes']) * len(results['merged_changes'][0]) if results['merged_changes'] else 0
            }
        }

        summary_file = os.path.join(output_dir, f"analysis_summary_{timestamp}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"  📋 分析摘要: {summary_file}")

        return output_dir

def main():
    """主函数"""
    print("🚀 开始分析不同版本间的数据变化差异")

    analyzer = VersionChangeAnalyzer()

    # 发现版本
    analyzer.discover_versions()

    if len(analyzer.versions) < 2:
        print("❌ 版本数量不足，无法进行变化分析")
        return

    # 分析变化
    results = analyzer.analyze_all_changes()

    # 保存结果
    output_dir = analyzer.save_results(results)

    print(f"\n✅ 分析完成！结果已保存到 {output_dir}/")

    # 显示总体统计
    total_changes = sum(len(changes) for changes in results['e2e_changes']) + \
                   sum(len(changes) for changes in results['interactivity_changes']) + \
                   sum(len(changes) for changes in results['merged_changes'])

    print(f"\n📊 总体统计:")
    print(f"  分析版本数: {len(analyzer.versions)}")
    print(f"  发现变化总数: {total_changes}")

if __name__ == "__main__":
    main()