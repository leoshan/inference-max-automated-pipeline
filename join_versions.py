#!/usr/bin/env python3
"""
将两个版本的merged CSV数据按照指定条件进行join操作
生成清晰的对比表格
"""

import pandas as pd

def join_version_data():
    """按条件join两个版本的数据"""

    print("🔄 加载版本1数据 (2025-10-23 16:54:52)...")
    v1_df = pd.read_csv('version_20251023_165452_merged.csv')
    print(f"   版本1记录数: {len(v1_df)}")

    print("🔄 加载版本2数据 (2025-10-24 15:06:50)...")
    v2_df = pd.read_csv('version_20251024_150650_merged.csv')
    print(f"   版本2记录数: {len(v2_df)}")

    # 定义join键
    join_keys = ['model_name', 'sequence_length', 'conc', 'tp', 'precision', 'hwKey']
    value_columns = ['e2e_x', 'e2e_y', 'inter_x', 'inter_y']

    print(f"\n🔑 Join键: {join_keys}")
    print(f"📊 数值列: {value_columns}")

    # 创建join键
    v1_df['join_key'] = v1_df[join_keys].astype(str).agg('|'.join, axis=1)
    v2_df['join_key'] = v2_df[join_keys].astype(str).agg('|'.join, axis=1)

    # 找到共同的键
    v1_keys = set(v1_df['join_key'])
    v2_keys = set(v2_df['join_key'])
    common_keys = v1_keys & v2_keys

    print(f"\n📈 Join统计:")
    print(f"   版本1唯一键: {len(v1_keys)}")
    print(f"   版本2唯一键: {len(v2_keys)}")
    print(f"   共同键: {len(common_keys)}")
    print(f"   仅版本1: {len(v1_keys - v2_keys)}")
    print(f"   仅版本2: {len(v2_keys - v1_keys)}")

    # 筛选共同记录
    v1_common = v1_df[v1_df['join_key'].isin(common_keys)].copy()
    v2_common = v2_df[v2_df['join_key'].isin(common_keys)].copy()

    # 按join键排序
    v1_common = v1_common.sort_values('join_key').reset_index(drop=True)
    v2_common = v2_common.sort_values('join_key').reset_index(drop=True)

    print(f"\n🔗 开始Join操作...")

    # 创建结果DataFrame
    result_records = []

    for idx in range(len(v1_common)):
        if idx >= len(v2_common):
            break

        v1_row = v1_common.iloc[idx]
        v2_row = v2_common.iloc[idx]

        # 确保join键一致
        if v1_row['join_key'] != v2_row['join_key']:
            print(f"⚠️  警告: Join键不一致 at index {idx}")
            continue

        # 创建结果记录
        result_record = {}

        # 添加join键字段
        for key in join_keys:
            result_record[key] = v1_row[key]

        # 添加版本1的数值
        for col in value_columns:
            result_record[f'{col}_v1'] = v1_row[col]

        # 添加版本2的数值
        for col in value_columns:
            result_record[f'{col}_v2'] = v2_row[col]

        # 计算差值
        for col in value_columns:
            v1_val = v1_row[col]
            v2_val = v2_row[col]

            if pd.notna(v1_val) and pd.notna(v2_val):
                abs_diff = v2_val - v1_val
                if v1_val != 0:
                    pct_diff = (abs_diff / abs(v1_val)) * 100
                else:
                    pct_diff = 0 if abs_diff == 0 else float('inf')

                result_record[f'{col}_diff'] = abs_diff
                result_record[f'{col}_pct_diff'] = pct_diff
            else:
                result_record[f'{col}_diff'] = None
                result_record[f'{col}_pct_diff'] = None

        result_records.append(result_record)

    print(f"📊 Join完成，生成 {len(result_records)} 条记录")

    # 创建结果DataFrame
    result_df = pd.DataFrame(result_records)

    # 重新排列列顺序
    base_columns = join_keys.copy()
    v1_columns = [f'{col}_v1' for col in value_columns]
    v2_columns = [f'{col}_v2' for col in value_columns]
    diff_columns = [f'{col}_diff' for col in value_columns]
    pct_columns = [f'{col}_pct_diff' for col in value_columns]

    all_columns = base_columns + v1_columns + v2_columns + diff_columns + pct_columns
    result_df = result_df[all_columns]

    # 保存到CSV文件
    output_file = 'version_joined_comparison.csv'
    result_df.to_csv(output_file, index=False)
    print(f"✅ Join结果已保存到: {output_file}")

    # 生成统计信息
    print(f"\n📈 Join结果统计:")
    print(f"   总记录数: {len(result_df)}")

    # 统计有差异的记录
    has_diff_count = 0
    for col in value_columns:
        diff_col = f'{col}_pct_diff'
        if diff_col in result_df.columns:
            diff_count = result_df[abs(result_df[diff_col]) > 0.1].shape[0]
            has_diff_count = max(has_diff_count, diff_count)
            print(f"   {col} 差异记录数: {diff_count} ({diff_count/len(result_df)*100:.1f}%)")

    print(f"   至少一个指标有差异的记录: {has_diff_count} ({has_diff_count/len(result_df)*100:.1f}%)")

    # 按模型分组统计
    print(f"\n🔍 按模型分组统计:")
    model_count = result_df.groupby('model_name').size()
    model_diff_stats = result_df.groupby('model_name').apply(
        lambda group: pd.Series({
            '总记录数': len(group),
            'e2e_x差异': (abs(group['e2e_x_pct_diff']) > 0.1).sum(),
            'e2e_y差异': (abs(group['e2e_y_pct_diff']) > 0.1).sum(),
            'inter_x差异': (abs(group['inter_x_pct_diff']) > 0.1).sum(),
            'inter_y差异': (abs(group['inter_y_pct_diff']) > 0.1).sum()
        })
    ).round(2)

    print(model_diff_stats.to_string())

    # 显示前几条记录示例
    print(f"\n🔝 前5条记录示例:")
    display_cols = join_keys + v1_columns + v2_columns
    print(result_df[display_cols].head().to_string(index=False, float_format='%.3f'))

    return result_df

if __name__ == "__main__":
    print("🚀 开始版本数据Join操作...")
    print("=" * 60)

    try:
        result_df = join_version_data()
        print(f"\n🎯 Join操作完成! 生成了 {len(result_df)} 条对比记录")
        print("📁 输出文件: version_joined_comparison.csv")

    except Exception as e:
        print(f"❌ Join过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()