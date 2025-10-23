#!/usr/bin/env python3
import json
import os
import glob
import csv
import re
from datetime import datetime

def normalize_sequence_format(sequence_str):
    """将序列格式标准化为 1k-1k, 1k-8k 等格式"""
    # 移除空格并转换为小写
    normalized = sequence_str.replace(' ', '').lower()
    # 将 "/" 替换为 "-"
    normalized = normalized.replace('/', '-')
    return normalized

def extract_all_fields(json_files):
    """提取所有可能的字段名"""
    all_fields = set()
    all_nested_fields = {}

    for filepath in json_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data_points = data.get('data', [])
            for point in data_points:
                if isinstance(point, dict):
                    for key, value in point.items():
                        if isinstance(value, dict):
                            # 嵌套对象，提取其字段
                            for nested_key in value.keys():
                                all_nested_fields[key] = all_nested_fields.get(key, set())
                                all_nested_fields[key].add(nested_key)
                        else:
                            all_fields.add(key)
        except Exception as e:
            print(f"Error extracting fields from {filepath}: {e}")

    # 将嵌套字段转换为扁平字段名
    flat_fields = set(all_fields)
    for parent_key, nested_keys in all_nested_fields.items():
        for nested_key in nested_keys:
            flat_fields.add(f"{parent_key}_{nested_key}")

    return sorted(list(flat_fields))

def flatten_data_point(data_point):
    """将嵌套的数据点扁平化"""
    flattened = {}

    for key, value in data_point.items():
        if isinstance(value, dict):
            # 处理嵌套对象
            for nested_key, nested_value in value.items():
                flattened[f"{key}_{nested_key}"] = nested_value
        else:
            flattened[key] = value

    return flattened

def process_json_files(directory):
    """处理目录下的所有JSON文件"""
    # 查找所有JSON文件（排除报告文件）
    json_files = glob.glob(os.path.join(directory, '*.json'))
    json_files = [f for f in json_files if not any(x in os.path.basename(f).lower()
                                               for x in ['readme', 'summary', 'cleanup', 'report'])]

    print(f"📊 Found {len(json_files)} JSON files to process")

    if not json_files:
        print("❌ No JSON files found!")
        return None

    # 提取所有可能的字段
    print("🔍 Analyzing data structure...")
    all_fields = extract_all_fields(json_files)
    print(f"📋 Found {len(all_fields)} unique data fields")

    # 定义CSV列的顺序
    csv_columns = ['model_name', 'sequence_length'] + all_fields

    # 准备CSV数据
    csv_data = []
    total_records = 0

    print("🔄 Processing JSON files...")
    for i, filepath in enumerate(json_files):
        filename = os.path.basename(filepath)
        print(f"  📄 Processing {i+1}/{len(json_files)}: {filename}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # 提取元数据
            metadata = json_data.get('metadata', {})
            model_name = metadata.get('model', 'Unknown')
            sequence_length = normalize_sequence_format(metadata.get('sequence', 'Unknown'))

            # 处理数据点
            data_points = json_data.get('data', [])
            file_records = 0

            for data_point in data_points:
                if isinstance(data_point, dict):
                    # 扁平化数据点
                    flattened_point = flatten_data_point(data_point)

                    # 创建CSV行
                    csv_row = {}

                    # 添加模型和序列列
                    csv_row['model_name'] = model_name
                    csv_row['sequence_length'] = sequence_length

                    # 添加所有数据字段
                    for field in all_fields:
                        csv_row[field] = flattened_point.get(field, '')

                    csv_data.append(csv_row)
                    file_records += 1

            total_records += file_records
            print(f"    ✅ Extracted {file_records} data points")

        except Exception as e:
            print(f"    ❌ Error processing {filename}: {e}")

    print(f"📊 Total records extracted: {total_records}")

    return csv_columns, csv_data

def generate_csv_summary(csv_data, output_file):
    """生成CSV数据的统计摘要"""
    if not csv_data:
        return

    # 统计信息
    total_records = len(csv_data)
    models = set()
    sequences = set()
    hardware = set()
    precisions = set()

    for row in csv_data:
        models.add(row.get('model_name', 'Unknown'))
        sequences.add(row.get('sequence_length', 'Unknown'))
        if row.get('hwKey'):
            hardware.add(row['hwKey'])
        if row.get('precision'):
            precisions.add(row['precision'])

    summary = {
        'generation_timestamp': datetime.now().isoformat(),
        'output_file': output_file,
        'total_records': total_records,
        'unique_models': list(models),
        'unique_sequences': list(sequences),
        'unique_hardware': list(hardware),
        'unique_precisions': list(precisions),
        'csv_columns': len(csv_data[0]) if csv_data else 0
    }

    return summary

def save_csv_file(csv_columns, csv_data, output_file):
    """保存CSV文件"""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)

            # 写入表头
            writer.writeheader()

            # 写入数据行
            writer.writerows(csv_data)

        print(f"✅ CSV file saved: {output_file}")
        return True

    except Exception as e:
        print(f"❌ Error saving CSV file: {e}")
        return False

def create_readable_summary(summary, csv_columns):
    """创建可读的摘要文件"""
    summary_text = f"""# InferenceMAX 数据集 CSV 转换报告

## 📊 转换统计
- **生成时间**: {summary['generation_timestamp']}
- **输出文件**: {summary['output_file']}
- **总记录数**: {summary['total_records']:,}
- **CSV列数**: {summary['csv_columns']}

## 🖥️ 数据概览
- **模型数量**: {len(summary['unique_models'])}
- **序列配置**: {len(summary['unique_sequences'])}
- **硬件平台**: {len(summary['unique_hardware'])}
- **精度类型**: {len(summary['unique_precisions'])}

## 📋 数据详情

### 模型列表
"""
    for model in sorted(summary['unique_models']):
        summary_text += f"- {model}\n"

    summary_text += f"""
### 序列配置
"""
    for seq in sorted(summary['unique_sequences']):
        summary_text += f"- {seq}\n"

    summary_text += f"""
### 硬件平台
"""
    for hw in sorted(summary['unique_hardware']):
        summary_text += f"- {hw}\n"

    summary_text += f"""
### 精度类型
"""
    for precision in sorted(summary['unique_precisions']):
        summary_text += f"- {precision}\n"

    summary_text += f"""
## 📄 CSV 列说明
前两列为标识列：
- **model_name**: 模型名称
- **sequence_length**: 序列长度配置

数据列包含性能指标：
- **conc**: 并发数
- **hwKey**: 硬件平台标识
- **precision**: 精度类型 (FP8/FP4)
- **tp**: 张量并行数
- **costh_y**: P50延迟 (毫秒)
- **costn_y**: P90延迟 (毫秒)
- **costr_y**: P99延迟 (毫秒)
- **tpPerGpu_y**: 每GPU吞吐量 (tokens/second)
- **tpPerMw_y**: 每兆瓦吞吐量
- **x**: X轴坐标 (延迟)
- **y**: Y轴坐标 (吞吐量)
- **costh_roof**, **costn_roof**, **costr_roof**: 是否达到性能上限
- **tpPerGpu_roof**, **tpPerMw_roof**: 是否达到性能上限

## 🔍 使用建议
1. **性能比较**: 按model_name分组比较不同硬件的性能
2. **序列影响**: 分析sequence_length对性能的影响
3. **硬件选择**: 根据hwKey选择最适合的硬件平台
4. **精度权衡**: 比较precision为fp8和fp4的性能差异

---

*此CSV文件由 InferenceMAX JSON数据转换生成*
"""

    return summary_text

def main():
    input_directory = 'json_data/raw_json_files'
    output_file = 'json_data/inference_max_dataset.csv'
    summary_file = 'json_data/CSV_CONVERSION_REPORT.md'

    if not os.path.exists(input_directory):
        print(f"❌ Input directory {input_directory} does not exist")
        return

    print("🚀 Starting JSON to CSV conversion...")

    # 处理JSON文件
    result = process_json_files(input_directory)
    if result is None:
        print("❌ No data to convert")
        return

    csv_columns, csv_data = result

    if not csv_data:
        print("❌ No data records found")
        return

    # 保存CSV文件
    print(f"\n💾 Saving CSV file...")
    if save_csv_file(csv_columns, csv_data, output_file):
        # 生成统计摘要
        summary = generate_csv_summary(csv_data, output_file)

        # 创建可读摘要
        readable_summary = create_readable_summary(summary, csv_columns)

        # 保存摘要文件
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(readable_summary)

        print(f"📋 Summary report saved: {summary_file}")

        # 显示文件信息
        file_size = os.path.getsize(output_file)
        print(f"\n🎉 Conversion completed successfully!")
        print(f"📄 Output file: {output_file}")
        print(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"📈 Total records: {len(csv_data):,}")
        print(f"📋 Columns: {len(csv_columns)}")

        # 显示前几行作为预览
        print(f"\n📋 Column preview:")
        print("Columns:", ", ".join(csv_columns[:10]) + "..." if len(csv_columns) > 10 else ", ".join(csv_columns))

        print(f"\n📊 Data preview (first 3 records):")
        for i, row in enumerate(csv_data[:3]):
            print(f"Record {i+1}:")
            print(f"  Model: {row.get('model_name', 'N/A')}")
            print(f"  Sequence: {row.get('sequence_length', 'N/A')}")
            print(f"  Hardware: {row.get('hwKey', 'N/A')}")
            print(f"  Precision: {row.get('precision', 'N/A')}")
            print(f"  Concurrency: {row.get('conc', 'N/A')}")
            print(f"  Throughput: {row.get('tpPerGpu_y', 'N/A')}")
            print()

if __name__ == "__main__":
    main()