#!/usr/bin/env python3
"""
直接通过API采集完整数据的脚本
"""

import requests
import json
import time
import os
from datetime import datetime

def fetch_model_data(model, sequence, data_type):
    """获取指定模型、序列和数据类型的JSON数据"""
    # 构建URL
    model_url = model.lower().replace(' ', '-').replace('.', '-')
    sequence_url = sequence.lower().replace(' / ', '_').replace('/', '_')

    url = f"https://inferencemax.semianalysis.com/data/inference-performance/{model_url}-{sequence_url}-{data_type}.json"

    print(f"📡 获取: {url}")

    try:
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功: {len(data)} 条记录")

            # 分析数据
            hwkeys = set()
            b200_trt_count = 0

            for item in data:
                hwkey = item.get('hwKey', '')
                hwkeys.add(str(hwkey))
                if 'b200_trt' in str(hwkey).lower():
                    b200_trt_count += 1

            print(f"📋 硬件类型: {sorted(hwkeys)}")
            print(f"🎯 b200_trt: {b200_trt_count} 条")

            return data, b200_trt_count, hwkeys
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return None, 0, set()

    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None, 0, set()

def save_json_file(data, model, sequence, data_type, response_index, output_dir):
    """保存JSON文件"""
    model_safe = model.replace(' ', '_').replace('.', '_')
    sequence_safe = sequence.replace(' ', '_').replace('/', '___')

    # 根据URL生成文件名
    model_url = model.lower().replace(' ', '-').replace('.', '-')
    sequence_url = sequence.lower().replace(' / ', '_').replace('/', '_')

    filename = f"{model_url}_{sequence_url}_{data_type}.json"
    filepath = os.path.join(output_dir, filename)

    file_data = {
        'metadata': {
            'model': model,
            'sequence': sequence,
            'data_type': data_type,
            'response_index': response_index,
            'timestamp': datetime.now().isoformat(),
            'source_url': f"https://inferencemax.semianalysis.com/data/inference-performance/{model_url}-{sequence_url}-{data_type}.json",
            'record_count': len(data) if data else 0
        },
        'data': data
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(file_data, f, indent=2, ensure_ascii=False)

    print(f"💾 保存: {filename} ({len(data) if data else 0} 条记录)")
    return filepath

def main():
    """主函数"""
    print("🚀 开始直接API数据采集...")

    # 定义要采集的数据
    models = [
        "Llama 3.3 70B Instruct",
        "gpt-oss 120B",
        "DeepSeek R1 0528"
    ]

    sequences = ["1K / 1K", "1K / 8K", "8K / 1K"]
    data_types = ["e2e", "interactivity"]

    # 创建输出目录
    output_dir = "json_data/api_raw_files"
    os.makedirs(output_dir, exist_ok=True)

    # 统计信息
    total_files = 0
    total_records = 0
    total_b200_trt = 0
    model_stats = {}

    print(f"📋 目标: {len(models)} 模型 × {len(sequences)} 序列 × {len(data_types)} 数据类型 = {len(models) * len(sequences) * len(data_types)} 个文件")
    print(f"📁 输出目录: {output_dir}")

    start_time = time.time()

    for model in models:
        model_stats[model] = {
            'files': 0,
            'records': 0,
            'b200_trt': 0,
            'hwkeys': set()
        }

        print(f"\n{'='*60}")
        print(f"🔍 处理模型: {model}")
        print(f"{'='*60}")

        for sequence in sequences:
            for data_type in data_types:
                print(f"\n📊 {model} + {sequence} ({data_type}):")

                # 获取数据
                data, b200_trt_count, hwkeys = fetch_model_data(model, sequence, data_type)

                if data:
                    # 保存文件
                    save_json_file(data, model, sequence, data_type, 1, output_dir)

                    # 更新统计
                    file_count = 1
                    record_count = len(data)

                    total_files += file_count
                    total_records += record_count
                    total_b200_trt += b200_trt_count

                    model_stats[model]['files'] += file_count
                    model_stats[model]['records'] += record_count
                    model_stats[model]['b200_trt'] += b200_trt_count
                    model_stats[model]['hwkeys'].update(hwkeys)

                time.sleep(1)  # 避免请求过快

    # 输出统计信息
    elapsed_time = time.time() - start_time

    print(f"\n{'='*80}")
    print(f"📈 采集统计:")
    print(f"{'='*80}")
    print(f"总耗时: {elapsed_time:.1f} 秒")
    print(f"总文件数: {total_files}")
    print(f"总记录数: {total_records}")
    print(f"总b200_trt数据: {total_b200_trt}")

    print(f"\n📊 各模型详细统计:")
    for model, stats in model_stats.items():
        hwkeys_list = sorted(list(stats['hwkeys']))
        has_b200_trt = 'b200_trt' in hwkeys_list

        print(f"\n🔸 {model}:")
        print(f"  文件数: {stats['files']}")
        print(f"  记录数: {stats['records']}")
        print(f"  b200_trt: {stats['b200_trt']} 条 {'✅' if has_b200_trt else '❌'}")
        print(f"  硬件类型: {hwkeys_list}")

    # 保存统计报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'elapsed_time': elapsed_time,
        'total_stats': {
            'files': total_files,
            'records': total_records,
            'b200_trt': total_b200_trt
        },
        'model_stats': {
            model: {
                'files': stats['files'],
                'records': stats['records'],
                'b200_trt': stats['b200_trt'],
                'hwkeys': sorted(list(stats['hwkeys']))
            }
            for model, stats in model_stats.items()
        }
    }

    report_file = os.path.join(output_dir, 'api_scraping_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📋 报告已保存: {report_file}")

    # 最终结论
    print(f"\n{'='*80}")
    print(f"🎯 最终结论:")
    print(f"{'='*80}")

    if total_b200_trt > 0:
        print(f"✅ 成功采集到 {total_b200_trt} 条 b200_trt 数据!")
        print(f"💡 网站确实有这些数据，之前的爬虫需要进一步修复")
    else:
        print(f"❌ 未采集到任何 b200_trt 数据")
        print(f"💡 这与直接API测试结果不符，需要进一步调试")

if __name__ == "__main__":
    main()