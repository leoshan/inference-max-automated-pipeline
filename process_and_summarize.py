#!/usr/bin/env python3
import json
import os
from datetime import datetime

def process_json_data():
    """处理和总结所有捕获的JSON数据"""

    # 查找所有JSON文件
    json_files = []
    for file in os.listdir('json_data'):
        if file.endswith('.json') and file.startswith('combo_'):
            json_files.append(file)

    print(f"Found {len(json_files)} combination JSON files")

    all_combinations = []
    summary_stats = {
        'total_combinations': len(json_files),
        'models_tested': set(),
        'sequences_tested': set(),
        'hardware_found': set(),
        'precisions_found': set(),
        'data_points_total': 0
    }

    for json_file in json_files:
        print(f"\nProcessing: {json_file}")

        try:
            with open(f'json_data/{json_file}', 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 提取基本信息
            model = data.get('model', 'Unknown')
            sequence = data.get('sequence', 'Unknown')
            timestamp = data.get('timestamp', 0)
            data_count = data.get('data_count', 0)

            summary_stats['models_tested'].add(model)
            summary_stats['sequences_tested'].add(sequence)
            summary_stats['data_points_total'] += data_count

            # 处理JSON响应
            json_responses = data.get('json_responses', [])

            for response in json_responses:
                response_data = response.get('data', [])

                for data_point in response_data:
                    # 提取硬件和精度信息
                    hw_key = data_point.get('hwKey', 'unknown')
                    precision = data_point.get('precision', 'unknown')

                    summary_stats['hardware_found'].add(hw_key)
                    summary_stats['precisions_found'].add(precision)

            # 创建简化的组合摘要
            combo_summary = {
                'file': json_file,
                'model': model,
                'sequence': sequence,
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp).isoformat(),
                'data_count': data_count,
                'hardware': list(set(dp.get('hwKey', 'unknown')
                                   for response in json_responses
                                   for dp in response.get('data', []))),
                'precisions': list(set(dp.get('precision', 'unknown')
                                     for response in json_responses
                                     for dp in response.get('data', []))),
                'concurrency_levels': list(set(dp.get('conc', 0)
                                              for response in json_responses
                                              for dp in response.get('data', [])))
            }

            all_combinations.append(combo_summary)

        except Exception as e:
            print(f"Error processing {json_file}: {e}")

    # 转换sets为lists以便JSON序列化
    summary_stats['models_tested'] = list(summary_stats['models_tested'])
    summary_stats['sequences_tested'] = list(summary_stats['sequences_tested'])
    summary_stats['hardware_found'] = list(summary_stats['hardware_found'])
    summary_stats['precisions_found'] = list(summary_stats['precisions_found'])

    # 创建最终报告
    final_report = {
        'report_generated': datetime.now().isoformat(),
        'summary_statistics': summary_stats,
        'combinations': all_combinations
    }

    # 保存总结报告
    with open('json_data/final_summary_report.json', 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    # 生成人类可读的摘要
    generate_readable_summary(final_report)

    return final_report

def generate_readable_summary(report):
    """生成人类可读的摘要"""

    stats = report['summary_statistics']
    combinations = report['combinations']

    summary_text = f"""
# InferenceMAX 数据抓取总结报告

生成时间: {report['report_generated']}

## 📊 总体统计
- **测试的组合总数**: {stats['total_combinations']}
- **捕获的数据点总数**: {stats['data_points_total']}
- **测试的模型**: {', '.join(stats['models_tested'])}
- **测试的序列**: {', '.join(stats['sequences_tested'])}

## 🖥️ 发现的硬件平台
{', '.join(stats['hardware_found'])}

## ⚙️ 发现的精度类型
{', '.join(stats['precisions_found'])}

## 📋 详细组合信息
"""

    for combo in combinations:
        summary_text += f"""
### {combo['model']} + {combo['sequence']}
- **文件**: {combo['file']}
- **测试时间**: {combo['datetime']}
- **数据点数量**: {combo['data_count']}
- **硬件**: {', '.join(combo['hardware']) if combo['hardware'] else 'N/A'}
- **精度**: {', '.join(combo['precisions']) if combo['precisions'] else 'N/A'}
- **并发级别**: {', '.join(map(str, combo['concurrency_levels'])) if combo['concurrency_levels'] else 'N/A'}

"""

    # 添加数据样本
    if combinations:
        first_combo = combinations[0]
        if first_combo['data_count'] > 0:
            summary_text += """
## 📈 数据样本
第一个组合捕获了详细的性能数据，包括：
- 吞吐量指标 (tokens/second)
- 延迟数据 (不同百分位数)
- 硬件效率指标
- 张量并行配置

完整数据请查看对应的JSON文件。

"""

    summary_text += """
## 📁 文件说明
- `final_summary_report.json`: 完整的结构化数据
- `combo_*.json`: 各个组合的详细JSON数据
- `initial_options.json`: 初始发现的选项
- `api_test_results.json`: API端点测试结果

## 🔍 数据分析建议
1. 比较不同硬件平台的性能表现
2. 分析精度对性能的影响
3. 研究并发级别与吞吐量的关系
4. 评估延迟与吞吐量的权衡

"""

    # 保存可读摘要
    with open('json_data/README.md', 'w', encoding='utf-8') as f:
        f.write(summary_text)

    print("✓ 生成可读摘要: json_data/README.md")

def main():
    print("🚀 开始处理和总结JSON数据...")

    if not os.path.exists('json_data'):
        print("❌ json_data目录不存在")
        return

    report = process_json_data()

    print("\n✅ 数据处理完成！")
    print(f"📊 处理了 {report['summary_statistics']['total_combinations']} 个组合")
    print(f"📈 总共捕获了 {report['summary_statistics']['data_points_total']} 个数据点")
    print(f"🖥️ 发现了 {len(report['summary_statistics']['hardware_found'])} 种硬件平台")
    print(f"⚙️ 发现了 {len(report['summary_statistics']['precisions_found'])} 种精度类型")

    print("\n📁 生成的文件:")
    print("- json_data/final_summary_report.json (完整数据)")
    print("- json_data/README.md (可读摘要)")

if __name__ == "__main__":
    main()