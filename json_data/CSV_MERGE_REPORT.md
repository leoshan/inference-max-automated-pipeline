# CSV文件合并报告

## 📊 合并统计
- **合并时间**: 2025-10-25T02:01:27.005265
- **输出文件**: json_data/inference_max_merged.csv
- **匹配的键数量**: 1393
- **仅E2E的键数量**: 0
- **仅Interactivity的键数量**: 0
- **总记录数**: 1393

## 📋 数据完整性验证

### x/y字段完整性
- **e2e_x**: 1393/1393 (100.0%)
- **e2e_y**: 1393/1393 (100.0%)
- **inter_x**: 1393/1393 (100.0%)
- **inter_y**: 1393/1393 (100.0%)

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
