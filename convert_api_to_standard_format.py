#!/usr/bin/env python3
"""
将API采集的JSON文件转换为标准格式，供管道处理使用
"""

import json
import os
import shutil
from datetime import datetime

def convert_api_file(api_file_path, output_file_path, model, sequence, data_type, combo_index):
    """转换单个API文件为标准格式"""

    # 读取API数据
    with open(api_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 检查数据格式
    if 'data' in data:
        actual_data = data['data']
    else:
        actual_data = data  # 如果没有data字段，说明本身就是数据数组

    # 分析数据
    hwkeys = set()
    b200_trt_count = 0
    for item in actual_data:
        hwkey = item.get('hwKey', '')
        hwkeys.add(str(hwkey))
        if 'b200_trt' in str(hwkey).lower():
            b200_trt_count += 1

    # 创建标准格式文件
    standard_data = {
        'metadata': {
            'combination_index': combo_index,
            'model': model,
            'sequence': sequence,
            'response_index': combo_index,
            'timestamp': datetime.now().isoformat(),
            'request_id': combo_index,
            'url': data.get('metadata', {}).get('source_url', 'unknown'),
            'method': 'GET',
            'content_type': 'application/json',
            'data_size': len(json.dumps(actual_data)),
            'data_type': data_type,
            'record_count': len(actual_data),
            'b200_trt_count': b200_trt_count,
            'hwkeys': sorted(list(hwkeys))
        },
        'data': actual_data
    }

    # 保存标准格式文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(standard_data, f, indent=2, ensure_ascii=False)

    print(f"✅ 转换: {os.path.basename(output_file_path)} ({len(actual_data)} 记录, {b200_trt_count} b200_trt)")

    return len(actual_data), b200_trt_count

def main():
    """主转换函数"""
    print("🔄 开始转换API文件为标准格式...")

    api_dir = "json_data/api_raw_files"
    output_dir = "json_data/raw_json_files"

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 定义文件映射
    file_mapping = [
        # gpt-oss 120B
        ("gpt-oss-120b_1k_1k_e2e.json", "gpt-oss 120B", "1K / 1K", "e2e", 4),
        ("gpt-oss-120b_1k_1k_interactivity.json", "gpt-oss 120B", "1K / 1K", "interactivity", 4),
        ("gpt-oss-120b_1k_8k_e2e.json", "gpt-oss 120B", "1K / 8K", "e2e", 5),
        ("gpt-oss-120b_1k_8k_interactivity.json", "gpt-oss 120B", "1K / 8K", "interactivity", 5),
        ("gpt-oss-120b_8k_1k_e2e.json", "gpt-oss 120B", "8K / 1K", "e2e", 6),
        ("gpt-oss-120b_8k_1k_interactivity.json", "gpt-oss 120B", "8K / 1K", "interactivity", 6),

        # DeepSeek R1 0528
        ("deepseek-r1-0528_1k_1k_e2e.json", "DeepSeek R1 0528", "1K / 1K", "e2e", 7),
        ("deepseek-r1-0528_1k_1k_interactivity.json", "DeepSeek R1 0528", "1K / 1K", "interactivity", 7),
        ("deepseek-r1-0528_1k_8k_e2e.json", "DeepSeek R1 0528", "1K / 8K", "e2e", 8),
        ("deepseek-r1-0528_1k_8k_interactivity.json", "DeepSeek R1 0528", "1K / 8K", "interactivity", 8),
        ("deepseek-r1-0528_8k_1k_e2e.json", "DeepSeek R1 0528", "8K / 1K", "e2e", 9),
        ("deepseek-r1-0528_8k_1k_interactivity.json", "DeepSeek R1 0528", "8K / 1K", "interactivity", 9),
    ]

    total_records = 0
    total_b200_trt = 0
    converted_files = 0

    print(f"📁 源目录: {api_dir}")
    print(f"📁 输出目录: {output_dir}")
    print()

    for api_file, model, sequence, data_type, combo_index in file_mapping:
        api_path = os.path.join(api_dir, api_file)

        if os.path.exists(api_path):
            # 生成标准格式文件名
            model_safe = model.replace(' ', '_').replace('.', '_')
            sequence_safe = sequence.replace(' ', '_').replace('/', '___')

            output_filename = f"{combo_index:02d}_{model_safe}_{sequence_safe}_{combo_index:02d}.json"
            output_path = os.path.join(output_dir, output_filename)

            # 转换文件
            try:
                records, b200_trt = convert_api_file(api_path, output_path, model, sequence, data_type, combo_index)
                total_records += records
                total_b200_trt += b200_trt
                converted_files += 1
            except Exception as e:
                print(f"❌ 转换失败 {api_file}: {str(e)}")
        else:
            print(f"⚠️ 文件不存在: {api_file}")

    print(f"\n📊 转换统计:")
    print(f"  转换文件数: {converted_files}")
    print(f"  总记录数: {total_records}")
    print(f"  总b200_trt数: {total_b200_trt}")

    # 保存转换报告
    conversion_report = {
        'timestamp': datetime.now().isoformat(),
        'total_files_converted': converted_files,
        'total_records': total_records,
        'total_b200_trt': total_b200_trt,
        'files_processed': file_mapping
    }

    report_path = os.path.join(output_dir, 'conversion_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(conversion_report, f, indent=2, ensure_ascii=False)

    print(f"📋 转换报告已保存: {report_path}")

    return converted_files > 0

if __name__ == "__main__":
    main()