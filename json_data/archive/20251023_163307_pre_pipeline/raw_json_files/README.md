# InferenceMAX 完整数据集

## 🎯 爬取目标达成

✅ **成功爬取了所有9个模型×序列组合的完整数据！**

- **3个模型**: Llama 3.3 70B Instruct, gpt-oss 120B, DeepSeek R1 0528
- **3个序列配置**: 1K/1K, 1K/8K, 8K/1K
- **9个组合**: 每个组合4个JSON响应文件
- **总计**: 36个原始JSON文件 (约1.3MB数据)

## 📊 数据结构

每个JSON文件包含：
```json
{
  "metadata": {
    "combination_index": 1,
    "model": "Llama 3.3 70B Instruct",
    "sequence": "1K / 1K",
    "response_index": 1,
    "url": "/data/inference-performance/llama-3_3-70b-instruct-fp8-1k_1k-interactivity.json",
    "data_size": 57368
  },
  "data": [
    {
      "conc": 16,                    // 并发数
      "costh": {"y": 1.072},         // P50延迟
      "costn": {"y": 1.376},         // P90延迟
      "costr": {"y": 1.521},         // P99延迟
      "hwKey": "mi355x",             // 硬件平台
      "precision": "fp8",            // 精度类型
      "tp": 8,                       // 张量并行数
      "tpPerGpu": {"y": 383.618},   // 每GPU吞吐量
      "tpPerMw": {"y": 144761.523}, // 每兆瓦吞吐量
      "x": 98.424,                   // X轴坐标(延迟)
      "y": 383.618                   // Y轴坐标(吞吐量)
    }
  ]
}
```

## 📁 文件命名规范

文件格式: `{组合索引:02d}_{模型名}_{序列配置}_{响应序号:02d}.json`

示例:
- `01_Llama_3_3_70B_Instruct_1K___1K_01.json` - 第1个组合的第1个响应
- `04_gpt-oss_120B_1K___1K_01.json` - 第4个组合的第1个响应

## 🖥️ 发现的硬件平台

从数据中识别出以下GPU平台：
- **NVIDIA**: H100, H200, H200 (TRT), B200, B200 (TRT), GB200, GB200 NVL72
- **AMD**: MI300X, MI325X, MI355X

## ⚙️ 精度类型

- **FP8**: 8位浮点精度
- **FP4**: 4位浮点精度

## 📈 数据分析建议

1. **性能比较**: 比较不同GPU在相同模型下的表现
2. **精度影响**: 分析FP8 vs FP4的性能差异
3. **模型特性**: 对比不同模型(Llama vs GPT vs DeepSeek)的推理特性
4. **序列长度**: 研究1K/1K vs 1K/8K vs 8K/1K配置的影响
5. **成本效益**: 使用tpPerMw指标评估能效比

## 📋 组合详情

| 组合 | 模型 | 序列 | 文件数 | 数据大小 |
|------|------|------|--------|----------|
| 1 | Llama 3.3 70B Instruct | 1K/1K | 4 | ~220KB |
| 2 | Llama 3.3 70B Instruct | 1K/8K | 4 | ~220KB |
| 3 | Llama 3.3 70B Instruct | 8K/1K | 4 | ~220KB |
| 4 | gpt-oss 120B | 1K/1K | 4 | ~126KB |
| 5 | gpt-oss 120B | 1K/8K | 4 | ~126KB |
| 6 | gpt-oss 120B | 8K/1K | 4 | ~126KB |
| 7 | DeepSeek R1 0528 | 1K/1K | 4 | ~103KB |
| 8 | DeepSeek R1 0528 | 1K/8K | 4 | ~66KB |
| 9 | DeepSeek R1 0528 | 8K/1K | 4 | ~48KB |

## 🔧 下一步建议

1. **数据合并**: 可以考虑将每个组合的多个响应文件合并为统一格式
2. **数据清洗**: 过滤掉空响应或错误响应
3. **可视化**: 创建性能对比图表
4. **统计分析**: 计算平均性能、最佳配置等指标

## 📞 爬取信息

- **爬取时间**: 2025-10-23 10:14-10:16 (UTC)
- **爬取工具**: Selenium + Python
- **成功率**: 9/9 组合 (100%)
- **数据完整性**: 所有组合均捕获到完整性能数据

---

*本数据集来源于 InferenceMAX by SemiAnalysis (https://inferencemax.semianalysis.com/)*