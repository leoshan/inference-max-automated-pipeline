#!/usr/bin/env python3
import csv
import os
from collections import defaultdict
from datetime import datetime

def read_csv_file(filepath):
    """读取CSV文件并返回字典数据"""
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def create_key_index(data, key_fields):
    """基于指定键字段创建索引"""
    index = defaultdict(list)

    for row in data:
        # 创建复合键
        key_parts = []
        for field in key_fields:
            key_parts.append(row.get(field, ''))

        key = '|'.join(key_parts)
        index[key].append(row)

    return index

def join_csv_files(e2e_data, interactivity_data, key_fields):
    """执行基于多键的join操作"""
    print(f"🔄 Creating index for E2E data...")
    e2e_index = create_key_index(e2e_data, key_fields)

    print(f"🔄 Creating index for Interactivity data...")
    interactivity_index = create_key_index(interactivity_data, key_fields)

    print(f"📊 E2E unique keys: {len(e2e_index)}")
    print(f"📊 Interactivity unique keys: {len(interactivity_index)}")

    # 执行join操作
    joined_data = []
    matched_keys = 0
    e2e_only_keys = 0
    inter_only_keys = 0

    # 首先处理E2E数据作为基础
    for key, e2e_rows in e2e_index.items():
        if key in interactivity_index:
            # 找到匹配的记录
            inter_rows = interactivity_index[key]

            # 处理多对多关系（虽然理论上应该是一对一）
            for e2e_row in e2e_rows:
                for inter_row in inter_rows:
                    # 创建合并后的行
                    joined_row = e2e_row.copy()

                    # 重命名E2E的x和y字段
                    if 'x' in e2e_row:
                        joined_row['e2e_x'] = e2e_row['x']
                        del joined_row['x']

                    if 'y' in e2e_row:
                        joined_row['e2e_y'] = e2e_row['y']
                        del joined_row['y']

                    # 添加Interactivity的x和y字段
                    if 'x' in inter_row:
                        joined_row['inter_x'] = inter_row['x']

                    if 'y' in inter_row:
                        joined_row['inter_y'] = inter_row['y']

                    joined_data.append(joined_row)

            matched_keys += 1
        else:
            # E2E独有的记录
            for e2e_row in e2e_rows:
                joined_row = e2e_row.copy()

                # 重命名E2E的x和y字段
                if 'x' in e2e_row:
                    joined_row['e2e_x'] = e2e_row['x']
                    del joined_row['x']

                if 'y' in e2e_row:
                    joined_row['e2e_y'] = e2e_row['y']
                    del joined_row['y']

                # 添加空的Interactivity字段
                joined_row['inter_x'] = ''
                joined_row['inter_y'] = ''

                joined_data.append(joined_row)

            e2e_only_keys += 1

    # 处理Interactivity独有的记录
    for key, inter_rows in interactivity_index.items():
        if key not in e2e_index:
            for inter_row in inter_rows:
                # 创建基础行（使用Interactivity数据，但其他字段用空值）
                joined_row = {}

                # 复制所有字段
                for field in inter_row:
                    if field in ['x', 'y']:
                        continue  # 跳过x和y，稍后处理
                    joined_row[field] = inter_row[field]

                # 添加空的E2E字段
                joined_row['e2e_x'] = ''
                joined_row['e2e_y'] = ''

                # 添加Interactivity的x和y字段
                if 'x' in inter_row:
                    joined_row['inter_x'] = inter_row['x']

                if 'y' in inter_row:
                    joined_row['inter_y'] = inter_row['y']

                joined_data.append(joined_row)

            inter_only_keys += 1

    print(f"✅ Matched keys: {matched_keys}")
    print(f"⚠️  E2E only keys: {e2e_only_keys}")
    print(f"⚠️  Interactivity only keys: {inter_only_keys}")
    print(f"📊 Total joined records: {len(joined_data)}")

    return joined_data, {
        'matched_keys': matched_keys,
        'e2e_only_keys': e2e_only_keys,
        'inter_only_keys': inter_only_keys,
        'total_records': len(joined_data)
    }

def define_output_columns(base_columns):
    """定义输出列的顺序"""
    # 基础列（来自E2E文件，除了x和y）
    exclude_columns = ['x', 'y']
    base_cols = [col for col in base_columns if col not in exclude_columns]

    # 添加新的列
    new_columns = ['e2e_x', 'e2e_y', 'inter_x', 'inter_y']

    return base_cols + new_columns

def save_joined_csv(data, columns, output_file):
    """保存合并后的CSV文件"""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)

        print(f"✅ Joined CSV saved: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error saving joined CSV: {e}")
        return False

def validate_joined_data(data, key_fields):
    """验证合并后的数据质量"""
    print("\n🔍 Validating joined data...")

    # 统计各字段的数据完整性
    field_stats = {}
    for field in ['e2e_x', 'e2e_y', 'inter_x', 'inter_y']:
        non_empty = sum(1 for row in data if row.get(field, '').strip())
        field_stats[field] = {
            'total': len(data),
            'non_empty': non_empty,
            'empty': len(data) - non_empty,
            'completeness': (non_empty / len(data)) * 100 if data else 0
        }

    for field, stats in field_stats.items():
        print(f"📊 {field}: {stats['non_empty']}/{stats['total']} ({stats['completeness']:.1f}%) complete")

    # 检查键字段的完整性
    key_completeness = {}
    for field in key_fields:
        non_empty = sum(1 for row in data if row.get(field, '').strip())
        key_completeness[field] = (non_empty / len(data)) * 100 if data else 0

    print(f"\n🔑 Key field completeness:")
    for field, completeness in key_completeness.items():
        print(f"   {field}: {completeness:.1f}%")

    return field_stats

def create_join_summary(stats, validation_stats, output_file):
    """创建join操作的摘要报告"""
    summary = {
        'join_timestamp': datetime.now().isoformat(),
        'output_file': output_file,
        'join_statistics': stats,
        'validation_statistics': validation_stats
    }

    summary_text = f"""# CSV文件合并报告

## 📊 合并统计
- **合并时间**: {summary['join_timestamp']}
- **输出文件**: {output_file}
- **匹配的键数量**: {stats['matched_keys']}
- **仅E2E的键数量**: {stats['e2e_only_keys']}
- **仅Interactivity的键数量**: {stats['inter_only_keys']}
- **总记录数**: {stats['total_records']}

## 📋 数据完整性验证

### x/y字段完整性
"""

    for field, field_stats in validation_stats.items():
        completeness = field_stats['completeness']
        summary_text += f"- **{field}**: {field_stats['non_empty']}/{field_stats['total']} ({completeness:.1f}%)\n"

    summary_text += f"""
## 🔄 合并说明
- **Join键**: model_name, sequence_length, conc, hwKey, precision, tp
- **基础数据**: 来自E2E CSV文件
- **重命名字段**:
  - E2E的x → e2e_x
  - E2E的y → e2e_y
  - Interactivity的x → inter_x
  - Interactivity的y → inter_y

## 📄 输出文件说明
合并后的CSV文件包含：
- 所有来自E2E文件的原始列（除了x和y）
- 4个新列：e2e_x, e2e_y, inter_x, inter_y
- 对于无法匹配的记录，相应字段为空值

## 🔍 使用建议
1. **完整匹配记录**: 可以同时分析e2e和interactivity的性能指标
2. **仅E2E记录**: 只有端到端性能数据
3. **仅Interactivity记录**: 只有交互式性能数据
4. **数据分析**: 可以比较两种场景下的性能差异

---

*此文件由 E2E 和 Interactivity CSV 合并生成*
"""

    return summary, summary_text

def main():
    e2e_file = 'json_data/inference_max_e2e.csv'
    interactivity_file = 'json_data/inference_max_interactivity.csv'
    output_file = 'json_data/inference_max_merged.csv'
    summary_file = 'json_data/CSV_MERGE_REPORT.md'

    # 定义join的键字段
    key_fields = ['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp']

    print("🚀 Starting CSV file merge operation...")

    # 检查输入文件
    if not os.path.exists(e2e_file):
        print(f"❌ E2E file not found: {e2e_file}")
        return

    if not os.path.exists(interactivity_file):
        print(f"❌ Interactivity file not found: {interactivity_file}")
        return

    # 读取CSV文件
    print(f"📖 Reading E2E file: {e2e_file}")
    e2e_data = read_csv_file(e2e_file)
    print(f"   Loaded {len(e2e_data)} records")

    print(f"📖 Reading Interactivity file: {interactivity_file}")
    interactivity_data = read_csv_file(interactivity_file)
    print(f"   Loaded {len(interactivity_data)} records")

    # 执行join操作
    print(f"\n🔄 Joining files on keys: {', '.join(key_fields)}")
    joined_data, stats = join_csv_files(e2e_data, interactivity_data, key_fields)

    if not joined_data:
        print("❌ No data to save")
        return

    # 定义输出列
    base_columns = e2e_data[0].keys() if e2e_data else []
    output_columns = define_output_columns(base_columns)

    print(f"📋 Output columns: {len(output_columns)}")

    # 保存合并后的文件
    if save_joined_csv(joined_data, output_columns, output_file):
        # 验证数据质量
        validation_stats = validate_joined_data(joined_data, key_fields)

        # 创建摘要报告
        summary, summary_text = create_join_summary(stats, validation_stats, output_file)

        # 保存摘要报告
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_text)

        # 显示结果
        file_size = os.path.getsize(output_file)
        print(f"\n🎉 CSV merge completed successfully!")
        print(f"📄 Output file: {output_file}")
        print(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"📈 Total records: {len(joined_data):,}")
        print(f"📋 Columns: {len(output_columns)}")
        print(f"📊 Match rate: {(stats['matched_keys']/(stats['matched_keys']+stats['e2e_only_keys']+stats['inter_only_keys'])*100):.1f}%")
        print(f"📋 Summary report: {summary_file}")

        # 显示列预览
        print(f"\n📋 Column preview:")
        print("Columns:", ", ".join(output_columns[:10]) + "..." if len(output_columns) > 10 else ", ".join(output_columns))

        # 显示数据预览
        print(f"\n📊 Data preview (first 3 records):")
        for i, row in enumerate(joined_data[:3]):
            print(f"Record {i+1}:")
            print(f"  Model: {row.get('model_name', 'N/A')}")
            print(f"  Sequence: {row.get('sequence_length', 'N/A')}")
            print(f"  Hardware: {row.get('hwKey', 'N/A')}")
            print(f"  Concurrency: {row.get('conc', 'N/A')}")
            print(f"  E2E coords: ({row.get('e2e_x', 'N/A')}, {row.get('e2e_y', 'N/A')})")
            print(f"  Inter coords: ({row.get('inter_x', 'N/A')}, {row.get('inter_y', 'N/A')})")
            print()

if __name__ == "__main__":
    main()