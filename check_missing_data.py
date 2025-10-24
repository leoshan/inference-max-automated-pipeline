#!/usr/bin/env python3
"""
检查数据缺失问题的脚本
"""

import json
import os
import pandas as pd
from collections import defaultdict, Counter

def load_json_files():
    """加载所有JSON文件"""
    data_dir = "json_data/raw_json_files"
    all_data = []

    for file_name in sorted(os.listdir(data_dir)):
        if file_name.endswith('.json'):
            file_path = os.path.join(data_dir, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.append(data)

    return all_data

def analyze_hwkey_distribution():
    """分析hwKey分布情况"""
    all_data = load_json_files()

    model_hwkey_counts = defaultdict(Counter)
    total_counts = Counter()

    for item in all_data:
        if 'data' in item and 'metadata' in item:
            model = item['metadata']['model']
            for record in item['data']:
                hwkey = record.get('hwKey', 'unknown')
                model_hwkey_counts[model][hwkey] += 1
                total_counts[hwkey] += 1

    print("🔍 分析hwKey分布情况:\n")

    for model, hwkey_counter in model_hwkey_counts.items():
        print(f"📊 {model}:")
        for hwkey, count in sorted(hwkey_counter.items()):
            print(f"  {hwkey}: {count}")
        print()

    print("📈 总体hwKey分布:")
    for hwkey, count in sorted(total_counts.items()):
        print(f"  {hwkey}: {count}")

    return model_hwkey_counts

def check_b200_trt_missing():
    """专门检查b200_trt缺失情况"""
    all_data = load_json_files()

    print("\n🎯 检查b200_trt数据缺失情况:\n")

    # 检查每个模型是否有b200_trt数据
    model_b200_trt_counts = defaultdict(int)
    model_total_records = defaultdict(int)

    for item in all_data:
        if 'data' in item and 'metadata' in item:
            model = item['metadata']['model']
            for record in item['data']:
                model_total_records[model] += 1
                hwkey = record.get('hwKey', '')
                if 'b200' in hwkey.lower() or 'trt' in hwkey.lower():
                    model_b200_trt_counts[model] += 1

    print("🔍 各模型b200_trt相关数据统计:")
    for model in sorted(model_total_records.keys()):
        total = model_total_records[model]
        b200_count = model_b200_trt_counts[model]
        print(f"  {model}: 总记录={total}, b200_trt相关={b200_count}")

    # 检查哪些模型缺少b200_trt
    print("\n❌ 缺少b200_trt数据的模型:")
    for model in sorted(model_total_records.keys()):
        if model_b200_trt_counts[model] == 0:
            print(f"  ❌ {model}: 完全没有b200_trt相关数据")
        elif model_b200_trt_counts[model] < 20:
            print(f"  ⚠️  {model}: 只有{model_b200_trt_counts[model]}条b200_trt相关数据，可能不完整")

    return model_b200_trt_counts

def check_inference_max_website():
    """检查InferenceMAX网站上gpt-oss 120B模型是否有b200_trt数据"""
    print("\n🌐 建议手动检查InferenceMAX网站:")
    print("1. 访问 https://inferencemax.semianalysis.com/")
    print("2. 选择 'gpt-oss 120B' 模型")
    print("3. 查看硬件选项中是否有 'b200_trt' 选项")
    print("4. 如果有该选项，说明网站有数据但爬取脚本有问题")
    print("5. 如果没有该选项，说明网站本身就没有这个数据组合")

def check_json_file_structure():
    """检查JSON文件结构，可能的数据源问题"""
    print("\n📋 检查JSON文件结构:")

    data_dir = "json_data/raw_json_files"

    # 检查gpt-oss 120B相关文件
    gpt_files = [f for f in os.listdir(data_dir) if 'gpt-oss' in f]

    for file_name in sorted(gpt_files):
        file_path = os.path.join(data_dir, file_name)

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'metadata' in data:
            model = data['metadata']['model']
            sequence = data['metadata']['sequence']
            response_type = 'interactivity' if 'interactivity' in data['metadata']['url'] else 'e2e'

            print(f"\n📄 {file_name}:")
            print(f"  模型: {model}")
            print(f"  序列: {sequence}")
            print(f"  类型: {response_type}")
            print(f"  URL: {data['metadata']['url']}")
            print(f"  数据条数: {len(data['data'])}")

            # 检查hwKey类型
            hwkeys = set()
            for record in data['data']:
                hwkeys.add(record.get('hwKey', 'unknown'))

            print(f"  hwKey类型: {sorted(hwkeys)}")

def main():
    print("🚀 开始检查数据缺失问题...")

    # 分析hwKey分布
    hwkey_distribution = analyze_hwkey_distribution()

    # 检查b200_trt缺失情况
    b200_trt_counts = check_b200_trt_missing()

    # 检查文件结构
    check_json_file_structure()

    # 建议下一步行动
    check_inference_max_website()

    print("\n🎯 结论和建议:")
    print("1. 如果网站有b200_trt选项但未爬取到，说明爬取脚本需要修复")
    print("2. 如果网站本身没有b200_trt选项，说明该数据组合不存在")
    print("3. 建议手动访问网站确认gpt-oss 120B模型的硬件选项")

if __name__ == "__main__":
    main()