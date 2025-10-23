#!/usr/bin/env python3
import json
import os
import glob
import csv
import re
from datetime import datetime

def normalize_sequence_format(sequence_str):
    """将序列格式标准化为 1k-1k, 1k-8k 等格式"""
    normalized = sequence_str.replace(' ', '').lower()
    normalized = normalized.replace('/', '-')
    return normalized

def categorize_json_file(filepath):
    """根据URL判断JSON文件类型"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        url = data.get('metadata', {}).get('url', '')

        if 'interactivity.json' in url:
            return 'interactivity'
        elif 'e2e.json' in url:
            return 'e2e'
        else:
            print(f"⚠️  Warning: Unknown file type for {filepath}")
            return None

    except Exception as e:
        print(f"Error categorizing {filepath}: {e}")
        return None

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
            for nested_key, nested_value in value.items():
                flattened[f"{key}_{nested_key}"] = nested_value
        else:
            flattened[key] = value

    return flattened

def process_json_files_by_type(directory):
    """按类型处理JSON文件"""
    # 查找所有JSON文件（排除报告文件）
    json_files = glob.glob(os.path.join(directory, '*.json'))
    json_files = [f for f in json_files if not any(x in os.path.basename(f).lower()
                                               for x in ['readme', 'summary', 'cleanup', 'report'])]

    print(f"📊 Found {len(json_files)} JSON files to process")

    if not json_files:
        print("❌ No JSON files found!")
        return None, None

    # 按类型分类文件
    interactivity_files = []
    e2e_files = []

    print("🔍 Categorizing files by type...")
    for filepath in json_files:
        file_type = categorize_json_file(filepath)
        if file_type == 'interactivity':
            interactivity_files.append(filepath)
        elif file_type == 'e2e':
            e2e_files.append(filepath)

    print(f"📋 Interactivity files: {len(interactivity_files)}")
    print(f"📋 E2E files: {len(e2e_files)}")

    if len(interactivity_files) != len(e2e_files):
        print(f"⚠️  Warning: Different number of files - Interactivity: {len(interactivity_files)}, E2E: {len(e2e_files)}")

    return interactivity_files, e2e_files

def convert_files_to_csv(files, file_type, output_file):
    """将指定类型的文件转换为CSV"""
    if not files:
        print(f"❌ No {file_type} files to process")
        return None

    print(f"\n🔄 Processing {file_type} files...")

    # 提取所有可能的字段
    print("🔍 Analyzing data structure...")
    all_fields = extract_all_fields(files)
    print(f"📋 Found {len(all_fields)} unique data fields for {file_type}")

    # 定义CSV列的顺序
    csv_columns = ['model_name', 'sequence_length'] + all_fields

    # 准备CSV数据
    csv_data = []
    total_records = 0

    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        print(f"  📄 Processing {i+1}/{len(files)}: {filename}")

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

    print(f"📊 Total {file_type} records extracted: {total_records}")

    # 保存CSV文件
    if save_csv_file(csv_columns, csv_data, output_file):
        return {
            'columns': csv_columns,
            'data': csv_data,
            'total_records': total_records,
            'file_count': len(files)
        }
    else:
        return None

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

def create_comprehensive_summary(interactivity_result, e2e_result):
    """创建综合报告"""
    summary = {
        'generation_timestamp': datetime.now().isoformat(),
        'interactivity': {
            'output_file': 'json_data/inference_max_interactivity.csv',
            'total_records': interactivity_result['total_records'] if interactivity_result else 0,
            'file_count': interactivity_result['file_count'] if interactivity_result else 0,
            'columns': len(interactivity_result['columns']) if interactivity_result else 0
        },
        'e2e': {
            'output_file': 'json_data/inference_max_e2e.csv',
            'total_records': e2e_result['total_records'] if e2e_result else 0,
            'file_count': e2e_result['file_count'] if e2e_result else 0,
            'columns': len(e2e_result['columns']) if e2e_result else 0
        }
    }

    # 统计模型和序列信息
    all_data = []
    if interactivity_result:
        all_data.extend(interactivity_result['data'])
    if e2e_result:
        all_data.extend(e2e_result['data'])

    if all_data:
        models = set()
        sequences = set()
        hardware = set()
        precisions = set()

        for row in all_data:
            models.add(row.get('model_name', 'Unknown'))
            sequences.add(row.get('sequence_length', 'Unknown'))
            if row.get('hwKey'):
                hardware.add(row['hwKey'])
            if row.get('precision'):
                precisions.add(row['precision'])

        summary['overview'] = {
            'unique_models': list(models),
            'unique_sequences': list(sequences),
            'unique_hardware': list(hardware),
            'unique_precisions': list(precisions),
            'total_combined_records': len(all_data)
        }

    return summary

def create_readable_summary(summary):
    """创建可读的摘要文件"""
    summary_text = f"""# InferenceMAX 分离数据集 CSV 转换报告

## 📊 转换统计
- **生成时间**: {summary['generation_timestamp']}
- **总记录数**: {summary.get('overview', {}).get('total_combined_records', 0):,}

## 📄 Interactivity 数据集
- **输出文件**: {summary['interactivity']['output_file']}
- **记录数**: {summary['interactivity']['total_records']:,}
- **文件数**: {summary['interactivity']['file_count']}
- **列数**: {summary['interactivity']['columns']}

## 📄 E2E 数据集
- **输出文件**: {summary['e2e']['output_file']}
- **记录数**: {summary['e2e']['total_records']:,}
- **文件数**: {summary['e2e']['file_count']}
- **列数**: {summary['e2e']['columns']}

## 🖥️ 数据概览
"""

    if 'overview' in summary:
        overview = summary['overview']
        summary_text += f"""- **模型数量**: {len(overview['unique_models'])}
- **序列配置**: {len(overview['unique_sequences'])}
- **硬件平台**: {len(overview['unique_hardware'])}
- **精度类型**: {len(overview['unique_precisions'])}

### 模型列表
"""
        for model in sorted(overview['unique_models']):
            summary_text += f"- {model}\n"

        summary_text += f"""
### 序列配置
"""
        for seq in sorted(overview['unique_sequences']):
            summary_text += f"- {seq}\n"

        summary_text += f"""
### 硬件平台
"""
        for hw in sorted(overview['unique_hardware']):
            summary_text += f"- {hw}\n"

        summary_text += f"""
### 精度类型
"""
        for precision in sorted(overview['unique_precisions']):
            summary_text += f"- {precision}\n"

    summary_text += f"""
## 📋 数据类型说明

### Interactivity 数据
- **用途**: 交互式推理性能分析
- **x字段含义**: 延迟时间（毫秒）
- **y字段含义**: 吞吐量（tokens/second）
- **适用场景**: 实时应用、聊天机器人等需要低延迟的场景

### E2E (End-to-End) 数据
- **用途**: 端到端推理性能分析
- **x字段含义**: 其他性能指标（可能是成本或其他度量）
- **y字段含义**: 相应的性能值
- **适用场景**: 批处理、离线分析等综合考虑的场景

## 📄 CSV 列说明
每个CSV文件包含以下列：
- **model_name**: 模型名称
- **sequence_length**: 序列长度配置 (1k-1k, 1k-8k, 8k-1k)
- **conc**: 并发数
- **hwKey**: 硬件平台标识
- **precision**: 精度类型 (FP8/FP4)
- **tp**: 张量并行数
- **costh_y**: P50延迟 (毫秒)
- **costn_y**: P90延迟 (毫秒)
- **costr_y**: P99延迟 (毫秒)
- **tpPerGpu_y**: 每GPU吞吐量 (tokens/second)
- **tpPerMw_y**: 每兆瓦吞吐量
- **x/y**: 坐标值（含义根据数据类型不同）
- **其他字段**: 各种性能上限标志

## 🔍 使用建议
1. **交互式场景**: 使用 interactivity.csv 进行延迟敏感的分析
2. **批处理场景**: 使用 e2e.csv 进行综合性能分析
3. **性能比较**: 可以分别对比两种类型的数据
4. **硬件选择**: 根据具体应用场景选择合适的数据集

---

*此CSV文件由 InferenceMAX JSON数据分离转换生成*
"""

    return summary_text

def main():
    input_directory = 'json_data/raw_json_files'
    interactivity_output = 'json_data/inference_max_interactivity.csv'
    e2e_output = 'json_data/inference_max_e2e.csv'
    summary_file = 'json_data/SEPARATED_CSV_CONVERSION_REPORT.md'

    if not os.path.exists(input_directory):
        print(f"❌ Input directory {input_directory} does not exist")
        return

    print("🚀 Starting separated JSON to CSV conversion...")

    # 按类型分类文件
    interactivity_files, e2e_files = process_json_files_by_type(input_directory)

    if not interactivity_files and not e2e_files:
        print("❌ No valid files found")
        return

    # 转换interactivity文件
    interactivity_result = None
    if interactivity_files:
        print(f"\n📊 Converting Interactivity files...")
        interactivity_result = convert_files_to_csv(interactivity_files, 'interactivity', interactivity_output)

    # 转换e2e文件
    e2e_result = None
    if e2e_files:
        print(f"\n📊 Converting E2E files...")
        e2e_result = convert_files_to_csv(e2e_files, 'e2e', e2e_output)

    if not interactivity_result and not e2e_result:
        print("❌ No data was converted")
        return

    # 生成综合报告
    summary = create_comprehensive_summary(interactivity_result, e2e_result)

    # 创建可读摘要
    readable_summary = create_readable_summary(summary)

    # 保存摘要文件
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(readable_summary)

    print(f"\n📋 Summary report saved: {summary_file}")

    # 显示转换结果
    print(f"\n🎉 Separated conversion completed successfully!")

    if interactivity_result:
        file_size = os.path.getsize(interactivity_output)
        print(f"📄 Interactivity CSV: {interactivity_output}")
        print(f"📊 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"📈 Records: {interactivity_result['total_records']:,}")

    if e2e_result:
        file_size = os.path.getsize(e2e_output)
        print(f"📄 E2E CSV: {e2e_output}")
        print(f"📊 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"📈 Records: {e2e_result['total_records']:,}")

    total_records = (interactivity_result['total_records'] if interactivity_result else 0) + \
                   (e2e_result['total_records'] if e2e_result else 0)
    print(f"📊 Total records across both files: {total_records:,}")

if __name__ == "__main__":
    main()