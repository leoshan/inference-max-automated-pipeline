# InferenceMAX 数据集 CSV 转换报告

## 📊 转换统计
- **生成时间**: 2025-10-23T11:21:19.054425
- **输出文件**: json_data/inference_max_dataset.csv
- **总记录数**: 2,678
- **CSV列数**: 18

## 🖥️ 数据概览
- **模型数量**: 3
- **序列配置**: 3
- **硬件平台**: 10
- **精度类型**: 2

## 📋 数据详情

### 模型列表
- DeepSeek R1 0528
- Llama 3.3 70B Instruct
- gpt-oss 120B

### 序列配置
- 1k-1k
- 1k-8k
- 8k-1k

### 硬件平台
- b200
- b200_trt
- gb200
- gb200_mtp
- h100
- h200
- h200_trt
- mi300x
- mi325x
- mi355x

### 精度类型
- fp4
- fp8

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
