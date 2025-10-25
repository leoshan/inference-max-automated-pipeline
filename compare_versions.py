#!/usr/bin/env python3
"""
比较两个版本的merged CSV文件，找出相同条件下的e2e和inter数值差异
"""

import pandas as pd
import numpy as np

def load_and_compare_versions():
    """加载并比较两个版本的数据"""

    print("🔄 加载版本1数据 (2025-10-23 16:54:52)...")
    v1_df = pd.read_csv('version_20251023_165452_merged.csv')
    print(f"   版本1记录数: {len(v1_df)}")

    print("🔄 加载版本2数据 (2025-10-24 15:06:50)...")
    v2_df = pd.read_csv('version_20251024_150650_merged.csv')
    print(f"   版本2记录数: {len(v2_df)}")

    # 定义比较的关键列
    key_columns = ['model_name', 'sequence_length', 'conc', 'tp', 'precision']
    value_columns = ['e2e_x', 'e2e_y', 'inter_x', 'inter_y']

    print(f"\n🔑 关键匹配列: {key_columns}")
    print(f"📊 比较数值列: {value_columns}")

    # 创建复合键用于匹配
    v1_df['match_key'] = v1_df[key_columns].astype(str).agg('|'.join, axis=1)
    v2_df['match_key'] = v2_df[key_columns].astype(str).agg('|'.join, axis=1)

    # 找到共同的记录
    v1_keys = set(v1_df['match_key'])
    v2_keys = set(v2_df['match_key'])
    common_keys = v1_keys & v2_keys

    print(f"\n📈 匹配统计:")
    print(f"   版本1唯一键: {len(v1_keys)}")
    print(f"   版本2唯一键: {len(v2_keys)}")
    print(f"   共同键: {len(common_keys)}")
    print(f"   仅版本1: {len(v1_keys - v2_keys)}")
    print(f"   仅版本2: {len(v2_keys - v1_keys)}")

    # 筛选共同记录
    v1_common = v1_df[v1_df['match_key'].isin(common_keys)].copy()
    v2_common = v2_df[v2_df['match_key'].isin(common_keys)].copy()

    # 按匹配键排序
    v1_common = v1_common.sort_values('match_key').reset_index(drop=True)
    v2_common = v2_common.sort_values('match_key').reset_index(drop=True)

    print(f"\n🔍 开始数值比较...")

    # 比较数值差异
    differences = []

    for idx in range(len(v1_common)):
        if idx >= len(v2_common):
            break

        v1_row = v1_common.iloc[idx]
        v2_row = v2_common.iloc[idx]

        # 确保匹配键一致
        if v1_row['match_key'] != v2_row['match_key']:
            print(f"⚠️  警告: 匹配键不一致 at index {idx}")
            continue

        diff_record = {
            'model_name': v1_row['model_name'],
            'sequence_length': v1_row['sequence_length'],
            'conc': v1_row['conc'],
            'tp': v1_row['tp'],
            'precision': v1_row['precision'],
            'hwKey_v1': v1_row['hwKey'],
            'hwKey_v2': v2_row['hwKey']
        }

        has_difference = False

        # 比较每个数值列
        for col in value_columns:
            v1_val = v1_row[col]
            v2_val = v2_row[col]

            # 记录两个版本的值
            diff_record[f'{col}_v1'] = v1_val
            diff_record[f'{col}_v2'] = v2_val

            # 计算差值和百分比差异
            if pd.notna(v1_val) and pd.notna(v2_val):
                abs_diff = abs(v2_val - v1_val)
                if v1_val != 0:
                    pct_diff = (abs_diff / abs(v1_val)) * 100
                else:
                    pct_diff = 0 if abs_diff == 0 else float('inf')

                diff_record[f'{col}_abs_diff'] = abs_diff
                diff_record[f'{col}_pct_diff'] = pct_diff

                # 如果有显著差异（绝对差值 > 0.001 或百分比差异 > 0.1%）
                if abs_diff > 0.001 or pct_diff > 0.1:
                    has_difference = True

        if has_difference:
            differences.append(diff_record)

    print(f"📊 发现差异记录数: {len(differences)}")

    if differences:
        # 创建差异DataFrame
        diff_df = pd.DataFrame(differences)

        # 按差异程度排序（以e2e_x的百分比差异为主要排序依据）
        if 'e2e_x_pct_diff' in diff_df.columns:
            diff_df = diff_df.sort_values('e2e_x_pct_diff', ascending=False)

        # 保存到CSV文件
        output_file = 'version_comparison_differences.csv'
        diff_df.to_csv(output_file, index=False)
        print(f"✅ 差异结果已保存到: {output_file}")

        # 显示统计信息
        print(f"\n📈 差异统计:")
        for col in value_columns:
            abs_col = f'{col}_abs_diff'
            pct_col = f'{col}_pct_diff'

            if abs_col in diff_df.columns:
                max_abs_diff = diff_df[abs_col].max()
                mean_abs_diff = diff_df[abs_col].mean()
                max_pct_diff = diff_df[pct_col].max()
                mean_pct_diff = diff_df[pct_col].mean()

                print(f"   {col}:")
                print(f"     最大绝对差值: {max_abs_diff:.6f}")
                print(f"     平均绝对差值: {mean_abs_diff:.6f}")
                print(f"     最大百分比差异: {max_pct_diff:.2f}%")
                print(f"     平均百分比差异: {mean_pct_diff:.2f}%")

        # 显示前几个最显著的差异
        print(f"\n🔝 前10个最显著差异:")
        display_cols = ['model_name', 'sequence_length', 'conc', 'tp', 'precision']
        for col in value_columns:
            display_cols.extend([f'{col}_v1', f'{col}_v2', f'{col}_abs_diff', f'{col}_pct_diff'])

        # 只选择存在的列
        available_cols = [col for col in display_cols if col in diff_df.columns]

        top_diffs = diff_df.head(10)[available_cols]
        print(top_diffs.to_string(index=False, float_format='%.6f'))

        return diff_df
    else:
        print("✅ 未发现显著差异")
        return pd.DataFrame()

if __name__ == "__main__":
    print("🚀 开始版本比较分析...")
    print("=" * 60)

    try:
        diff_df = load_and_compare_versions()

        if len(diff_df) > 0:
            print(f"\n🎯 比较完成! 发现 {len(diff_df)} 条有差异的记录")
        else:
            print(f"\n🎯 比较完成! 两个版本数据一致")

    except Exception as e:
        print(f"❌ 比较过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()