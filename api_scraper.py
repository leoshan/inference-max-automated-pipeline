#!/usr/bin/env python3
"""
基于API的直接数据采集器 - 替换原有的网页爬取方法
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

class APIDataCollector:
    """API数据采集器"""

    def __init__(self):
        self.base_url = "https://inferencemax.semianalysis.com/data/inference-performance"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def normalize_model_name(self, model: str) -> str:
        """标准化模型名称用于URL"""
        normalized = model.lower().replace(' ', '-')
        # 先处理3.3 -> 3_3，再处理其他的. -> -
        normalized = normalized.replace('3.3', '3_3')
        normalized = normalized.replace('.', '-')
        return normalized

    def normalize_sequence_name(self, sequence: str) -> str:
        """标准化序列名称用于URL"""
        return sequence.lower().replace(' / ', '_').replace('/', '_')

    def normalize_llama_sequence_name(self, sequence: str) -> str:
        """为Llama模型标准化序列名称，匹配特定的URL格式"""
        # 处理 "1K / 1K" -> "1k_1k", "1K / 8K" -> "1k_8k", "8K / 1K" -> "8k_1k"
        return sequence.lower().replace(' ', '').replace('/', '_')

    def _generate_url(self, model: str, sequence: str, data_type: str, precision: str = 'fp8') -> str:
        """生成请求URL，与fetch_data方法保持一致"""
        model_url = self.normalize_model_name(model)

        if 'llama' in model_url.lower():
            sequence_url = self.normalize_llama_sequence_name(sequence)
            return f"{self.base_url}/{model_url}-{precision}-{sequence_url}-{data_type}.json"
        else:
            sequence_url = self.normalize_sequence_name(sequence)
            return f"{self.base_url}/{model_url}-{sequence_url}-{data_type}.json"

    def fetch_data(self, model: str, sequence: str, data_type: str) -> Tuple[Optional[List], bool]:
        """获取指定数据"""
        model_url = self.normalize_model_name(model)

        # 为Llama模型使用特殊的序列名称格式
        if 'llama' in model_url.lower():
            sequence_url = self.normalize_llama_sequence_name(sequence)
            url = f"{self.base_url}/{model_url}-fp8-{sequence_url}-{data_type}.json"
        else:
            sequence_url = self.normalize_sequence_name(sequence)
            url = f"{self.base_url}/{model_url}-{sequence_url}-{data_type}.json"

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return data, True
            else:
                logging.warning(f"HTTP {response.status_code} for {url}")
                return None, False

        except Exception as e:
            logging.error(f"Failed to fetch {url}: {str(e)}")
            return None, False

    def analyze_data(self, data: List[Dict]) -> Dict:
        """分析数据统计信息"""
        if not data:
            return {
                'record_count': 0,
                'hwkeys': set(),
                'b200_trt_count': 0,
                'has_b200_trt': False
            }

        hwkeys = set()
        b200_trt_count = 0

        for item in data:
            hwkey = item.get('hwKey', '')
            hwkeys.add(str(hwkey))
            if 'b200_trt' in str(hwkey).lower():
                b200_trt_count += 1

        return {
            'record_count': len(data),
            'hwkeys': hwkeys,
            'b200_trt_count': b200_trt_count,
            'has_b200_trt': b200_trt_count > 0
        }

    def save_json_file(self, data: List[Dict], model: str, sequence: str, data_type: str,
                      output_dir: str, response_index: int = 1) -> str:
        """保存JSON文件"""
        os.makedirs(output_dir, exist_ok=True)

        model_safe = model.replace(' ', '_').replace('.', '_')
        sequence_safe = sequence.replace(' ', '_').replace('/', '___')

        filename = f"{response_index:02d}_{model_safe}_{sequence_safe}_{data_type}.json"
        filepath = os.path.join(output_dir, filename)

        # 分析数据
        analysis = self.analyze_data(data)

        file_data = {
            'metadata': {
                'combination_index': response_index,
                'model': model,
                'sequence': sequence,
                'response_index': response_index,
                'timestamp': datetime.now().isoformat(),
                'request_id': response_index,
                'url': self._generate_url(model, sequence, data_type),
                'method': 'GET',
                'content_type': 'application/json',
                'data_size': len(json.dumps(data)),
                'data_type': data_type,
                'record_count': analysis['record_count'],
                'b200_trt_count': analysis['b200_trt_count'],
                'hwkeys': sorted(list(analysis['hwkeys']))
            },
            'data': data
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Saved: {filename} ({analysis['record_count']} records, {analysis['b200_trt_count']} b200_trt)")
        return filepath

    def collect_all_data(self, models: List[str], sequences: List[str],
                        output_dir: str) -> Dict:
        """采集所有数据"""
        data_types = ["e2e", "interactivity"]
        results = {
            'successful_collections': [],
            'failed_collections': [],
            'total_files': 0,
            'total_records': 0,
            'total_b200_trt': 0,
            'model_stats': {}
        }

        for model in models:
            model_stats = {
                'files': 0,
                'records': 0,
                'b200_trt': 0,
                'hwkeys': set(),
                'successful_combinations': 0
            }

            combination_index = 1

            for sequence in sequences:
                combination_data = {
                    'model': model,
                    'sequence': sequence,
                    'data_types': {},
                    'timestamp': datetime.now().isoformat()
                }

                combination_success = False

                for data_type in data_types:
                    print(f"\n📊 Collecting {model} + {sequence} ({data_type})...")

                    data, success = self.fetch_data(model, sequence, data_type)

                    if success and data:
                        try:
                            # 保存文件
                            filepath = self.save_json_file(data, model, sequence, data_type,
                                                         output_dir, combination_index)

                            # 分析数据
                            analysis = self.analyze_data(data)

                            # 更新统计
                            model_stats['files'] += 1
                            model_stats['records'] += analysis['record_count']
                            model_stats['b200_trt'] += analysis['b200_trt_count']
                            model_stats['hwkeys'].update(analysis['hwkeys'])

                            results['total_files'] += 1
                            results['total_records'] += analysis['record_count']
                            results['total_b200_trt'] += analysis['b200_trt_count']

                            combination_data['data_types'][data_type] = {
                                'success': True,
                                'record_count': analysis['record_count'],
                                'b200_trt_count': analysis['b200_trt_count'],
                                'hwkeys': sorted(list(analysis['hwkeys'])),
                                'filepath': filepath
                            }

                            combination_success = True
                            print(f"✅ Success: {analysis['record_count']} records, {analysis['b200_trt_count']} b200_trt")

                        except Exception as e:
                            print(f"❌ Failed to save file: {str(e)}")
                            combination_data['data_types'][data_type] = {
                                'success': False,
                                'error': str(e)
                            }
                    else:
                        print(f"❌ Failed to fetch data")
                        combination_data['data_types'][data_type] = {
                            'success': False,
                            'error': 'Failed to fetch data'
                        }

                    time.sleep(0.5)  # 避免请求过快

                if combination_success:
                    model_stats['successful_combinations'] += 1
                    results['successful_collections'].append(combination_data)
                else:
                    results['failed_collections'].append(combination_data)

                combination_index += 1

            # 转换hwkeys为列表以便JSON序列化
            model_stats['hwkeys'] = sorted(list(model_stats['hwkeys']))
            results['model_stats'][model] = model_stats

        return results


def scrape_api_data(models: List[str], sequences: List[str],
                    output_dir: str = "json_data/raw_json_files") -> Dict:
    """
    使用API方法采集数据的入口函数

    Args:
        models: 模型列表
        sequences: 序列长度列表
        output_dir: 输出目录

    Returns:
        采集结果字典
    """
    print("🚀 Starting API-based InferenceMAX data collection...")
    print(f"📋 Target: {len(models)} models × {len(sequences)} sequences = {len(models) * len(sequences)} combinations")
    print(f"📁 Output directory: {output_dir}")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 创建采集器
    collector = APIDataCollector()

    # 开始采集
    start_time = time.time()
    results = collector.collect_all_data(models, sequences, output_dir)
    elapsed_time = time.time() - start_time

    # 更新统计
    results['elapsed_time'] = elapsed_time
    results['timestamp'] = datetime.now().isoformat()

    # 打印结果
    print(f"\n{'='*80}")
    print(f"📈 Collection Statistics:")
    print(f"{'='*80}")
    print(f"Elapsed time: {elapsed_time:.1f} seconds")
    print(f"Total files: {results['total_files']}")
    print(f"Total records: {results['total_records']}")
    print(f"Total b200_trt data: {results['total_b200_trt']}")
    print(f"Successful combinations: {len(results['successful_collections'])}")

    print(f"\n📊 Model Details:")
    for model, stats in results['model_stats'].items():
        print(f"\n🔸 {model}:")
        print(f"  Files: {stats['files']}")
        print(f"  Records: {stats['records']}")
        print(f"  b200_trt: {stats['b200_trt']} ({'✅' if stats['b200_trt'] > 0 else '❌'})")
        print(f"  Hardware: {stats['hwkeys']}")

    # 保存总结报告
    summary_file = os.path.join(output_dir, 'api_scraping_summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📋 Summary saved: {summary_file}")

    return results


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 定义要采集的数据
    models = [
        "Llama 3.3 70B Instruct",
        "gpt-oss 120B",
        "DeepSeek R1 0528"
    ]

    sequences = ["1K / 1K", "1K / 8K", "8K / 1K"]

    # 执行采集
    results = scrape_api_data(models, sequences)