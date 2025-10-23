#!/usr/bin/env python3
import json
import os
import glob
from pathlib import Path

def analyze_json_file(filepath):
    """分析单个JSON文件的质量"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 获取文件大小
        file_size = os.path.getsize(filepath)

        # 检查基本结构
        if not isinstance(data, dict):
            return {
                'valid': False,
                'reason': 'Root is not a dictionary',
                'file_size': file_size
            }

        # 检查metadata和data字段
        if 'metadata' not in data or 'data' not in data:
            return {
                'valid': False,
                'reason': 'Missing metadata or data field',
                'file_size': file_size
            }

        # 检查data字段是否为空
        data_content = data.get('data', [])
        if not data_content:
            return {
                'valid': False,
                'reason': 'Data field is empty',
                'file_size': file_size
            }

        # 检查data字段是否有有效数据点
        valid_data_points = 0
        for item in data_content:
            if isinstance(item, dict):
                # 检查是否包含关键的性能指标
                if any(key in item for key in ['conc', 'tpPerGpu', 'hwKey', 'precision']):
                    # 检查是否有数值数据
                    has_numeric_values = False
                    for key, value in item.items():
                        if isinstance(value, (int, float)) and value > 0:
                            has_numeric_values = True
                            break

                    if has_numeric_values:
                        valid_data_points += 1

        if valid_data_points == 0:
            return {
                'valid': False,
                'reason': 'No valid data points with numeric values',
                'file_size': file_size,
                'total_data_points': len(data_content)
            }

        # 检查文件大小阈值（小于1KB通常没有有效数据）
        if file_size < 1024:
            return {
                'valid': False,
                'reason': f'File too small ({file_size} bytes)',
                'file_size': file_size,
                'valid_data_points': valid_data_points
            }

        return {
            'valid': True,
            'file_size': file_size,
            'total_data_points': len(data_content),
            'valid_data_points': valid_data_points,
            'metadata': data.get('metadata', {})
        }

    except json.JSONDecodeError as e:
        return {
            'valid': False,
            'reason': f'JSON decode error: {str(e)}',
            'file_size': os.path.getsize(filepath) if os.path.exists(filepath) else 0
        }
    except Exception as e:
        return {
            'valid': False,
            'reason': f'Error reading file: {str(e)}',
            'file_size': os.path.getsize(filepath) if os.path.exists(filepath) else 0
        }

def analyze_all_files(directory):
    """分析目录下所有JSON文件"""
    json_files = glob.glob(os.path.join(directory, '*.json'))

    # 排除README和summary文件
    json_files = [f for f in json_files if not any(x in os.path.basename(f) for x in ['README', 'summary'])]

    analysis_results = []

    print(f"📊 Analyzing {len(json_files)} JSON files...")

    for filepath in json_files:
        filename = os.path.basename(filepath)
        print(f"🔍 Analyzing: {filename}")

        result = analyze_json_file(filepath)
        result['filename'] = filename
        result['filepath'] = filepath
        analysis_results.append(result)

        status = "✅ Valid" if result['valid'] else "❌ Invalid"
        reason = result.get('reason', '')
        size = result.get('file_size', 0)

        print(f"   {status} - Size: {size:,} bytes - {reason}")

    return analysis_results

def remove_invalid_files(results, dry_run=True):
    """移除无效文件"""
    invalid_files = [r for r in results if not r['valid']]

    print(f"\n🗑️  Found {len(invalid_files)} invalid files")

    if not invalid_files:
        print("✅ All files are valid!")
        return []

    if dry_run:
        print("\n🔍 DRY RUN - Files that would be removed:")
        for result in invalid_files:
            print(f"   - {result['filename']} ({result['file_size']} bytes) - {result['reason']}")
        return invalid_files

    print("\n🗑️  Removing invalid files...")
    removed_files = []

    for result in invalid_files:
        try:
            os.remove(result['filepath'])
            removed_files.append(result['filename'])
            print(f"   ✅ Removed: {result['filename']}")
        except Exception as e:
            print(f"   ❌ Failed to remove {result['filename']}: {e}")

    return removed_files

def generate_cleanup_report(results, removed_files=None):
    """生成清理报告"""
    valid_files = [r for r in results if r['valid']]
    invalid_files = [r for r in results if not r['valid']]

    # 统计信息
    total_size = sum(r['file_size'] for r in results)
    valid_size = sum(r['file_size'] for r in valid_files)
    invalid_size = sum(r['file_size'] for r in invalid_files)

    # 按模型分组统计
    model_stats = {}
    for result in valid_files:
        metadata = result.get('metadata', {})
        model = metadata.get('model', 'Unknown')
        if model not in model_stats:
            model_stats[model] = {'files': 0, 'size': 0, 'data_points': 0}
        model_stats[model]['files'] += 1
        model_stats[model]['size'] += result['file_size']
        model_stats[model]['data_points'] += result.get('valid_data_points', 0)

    report = {
        'cleanup_timestamp': os.path.getmtime('.'),
        'summary': {
            'total_files': len(results),
            'valid_files': len(valid_files),
            'invalid_files': len(invalid_files),
            'removed_files': len(removed_files) if removed_files else 0,
            'total_size_bytes': total_size,
            'valid_size_bytes': valid_size,
            'invalid_size_bytes': invalid_size,
            'space_saved_bytes': invalid_size
        },
        'model_statistics': model_stats,
        'valid_files_detail': [
            {
                'filename': r['filename'],
                'model': r.get('metadata', {}).get('model', 'Unknown'),
                'sequence': r.get('metadata', {}).get('sequence', 'Unknown'),
                'file_size_bytes': r['file_size'],
                'data_points': r.get('valid_data_points', 0)
            } for r in valid_files
        ],
        'invalid_files_detail': [
            {
                'filename': r['filename'],
                'file_size_bytes': r['file_size'],
                'reason': r['reason']
            } for r in invalid_files
        ]
    }

    # 保存报告
    report_path = 'json_data/raw_json_files/cleanup_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 生成可读摘要
    readable_report = f"""# JSON文件清理报告

## 📊 总体统计
- **原始文件总数**: {len(results)}
- **有效文件数**: {len(valid_files)}
- **无效文件数**: {len(invalid_files)}
- **已删除文件数**: {len(removed_files) if removed_files else 0}
- **原始总大小**: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)
- **有效数据大小**: {valid_size:,} bytes ({valid_size/1024/1024:.2f} MB)
- **节省空间**: {invalid_size:,} bytes ({invalid_size/1024/1024:.2f} MB)

## 🖥️ 按模型统计
"""

    for model, stats in model_stats.items():
        readable_report += f"""
### {model}
- **文件数**: {stats['files']}
- **数据大小**: {stats['size']:,} bytes ({stats['size']/1024/1024:.2f} MB)
- **数据点数**: {stats['data_points']}
"""

    readable_report += f"""
## ✅ 有效文件列表 ({len(valid_files)}个)
"""

    for r in valid_files:
        metadata = r.get('metadata', {})
        model = metadata.get('model', 'Unknown')
        sequence = metadata.get('sequence', 'Unknown')
        readable_report += f"- **{r['filename']}** - {model} + {sequence} ({r['file_size']:,} bytes, {r.get('valid_data_points', 0)} 数据点)\n"

    if invalid_files:
        readable_report += f"""
## ❌ 无效文件列表 ({len(invalid_files)}个)
"""
        for r in invalid_files:
            readable_report += f"- **{r['filename']}** - {r['file_size']:,} bytes - {r['reason']}\n"

    # 保存可读报告
    readable_report_path = 'json_data/raw_json_files/CLEANUP_REPORT.md'
    with open(readable_report_path, 'w', encoding='utf-8') as f:
        f.write(readable_report)

    print(f"\n📋 Reports generated:")
    print(f"   - JSON report: {report_path}")
    print(f"   - Readable report: {readable_report_path}")

    return report

def main():
    directory = 'json_data/raw_json_files'

    if not os.path.exists(directory):
        print(f"❌ Directory {directory} does not exist")
        return

    print("🚀 Starting JSON file cleanup analysis...")

    # 分析所有文件
    results = analyze_all_files(directory)

    # 生成初始报告
    print("\n📊 Generating initial analysis report...")
    generate_cleanup_report(results)

    # 先进行干运行
    print("\n🔍 Performing dry run...")
    invalid_files = remove_invalid_files(results, dry_run=True)

    if not invalid_files:
        print("\n✅ No invalid files found. All files are valid!")
        return

    # 询问是否继续删除
    print(f"\n⚠️  Found {len(invalid_files)} invalid files.")
    print("These files will be permanently deleted.")

    # 自动删除无效文件（根据需求）
    print("\n🗑️  Removing invalid files...")
    removed_files = remove_invalid_files(results, dry_run=False)

    if removed_files:
        print(f"\n✅ Successfully removed {len(removed_files)} invalid files")

        # 重新分析清理后的文件
        print("\n📊 Re-analyzing files after cleanup...")
        remaining_files = glob.glob(os.path.join(directory, '*.json'))
        remaining_files = [f for f in remaining_files if not any(x in os.path.basename(f) for x in ['README', 'summary', 'cleanup', 'CLEANUP'])]

        final_results = []
        for filepath in remaining_files:
            result = analyze_json_file(filepath)
            result['filename'] = os.path.basename(filepath)
            result['filepath'] = filepath
            final_results.append(result)

        # 生成最终报告
        generate_cleanup_report(final_results, removed_files)

        print(f"\n🎉 Cleanup completed!")
        print(f"📁 Remaining valid files: {len(final_results)}")
        print(f"💾 Total valid data size: {sum(r['file_size'] for r in final_results):,} bytes")

if __name__ == "__main__":
    main()