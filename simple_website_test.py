#!/usr/bin/env python3
"""
简化的网站测试脚本 - 专门检查gpt-oss 120B的b200_trt数据
"""

import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def test_direct_api_calls():
    """直接测试API调用"""
    print("🔍 测试直接API调用...")

    # 测试gpt-oss 120B的API端点
    test_urls = [
        "https://inferencemax.semianalysis.com/data/inference-performance/gpt-oss-120b-1k_1k-e2e.json",
        "https://inferencemax.semianalysis.com/data/inference-performance/gpt-oss-120b-1k_1k-interactivity.json",
        "https://inferencemax.semianalysis.com/data/inference-performance/gpt-oss-120b-1k_8k-e2e.json",
        "https://inferencemax.semianalysis.com/data/inference-performance/gpt-oss-120b-1k_8k-interactivity.json",
        "https://inferencemax.semianalysis.com/data/inference-performance/gpt-oss-120b-8k_1k-e2e.json",
        "https://inferencemax.semianalysis.com/data/inference-performance/gpt-oss-120b-8k_1k-interactivity.json",
    ]

    for url in test_urls:
        try:
            print(f"\n📡 测试URL: {url}")
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功获取数据: {len(data)} 条记录")

                # 检查b200_trt数据
                b200_trt_count = 0
                all_hwkeys = set()

                for item in data:
                    hwkey = item.get('hwKey', '')
                    all_hwkeys.add(str(hwkey))
                    if 'b200_trt' in str(hwkey).lower():
                        b200_trt_count += 1

                print(f"📋 硬件类型: {sorted(all_hwkeys)}")
                print(f"🎯 b200_trt数据: {b200_trt_count} 条")

                if b200_trt_count > 0:
                    print("🎉 发现b200_trt数据!")
                    return True

            else:
                print(f"❌ HTTP错误: {response.status_code}")

        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")

    return False

def test_with_browser():
    """使用浏览器测试"""
    print("\n🌐 使用浏览器测试...")

    driver = setup_driver()

    try:
        # 设置网络监控
        monitoring_script = """
        window.capturedUrls = [];
        window.capturedData = [];

        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const url = args[0];
            const urlStr = typeof url === 'string' ? url : (url.url || '');

            if (urlStr.includes('gpt-oss') && urlStr.includes('.json')) {
                window.capturedUrls.push(urlStr);

                return originalFetch.apply(this, args).then(response => {
                    const clonedResponse = response.clone();
                    clonedResponse.json().then(data => {
                        window.capturedData.push({url: urlStr, data: data});
                        console.log('🔍 Captured GPT data:', urlStr);
                    });
                    return response;
                });
            }

            return originalFetch.apply(this, args);
        };
        """

        # 访问网站
        driver.get("https://inferencemax.semianalysis.com/")
        time.sleep(3)

        # 设置监控
        driver.execute_script(monitoring_script)
        time.sleep(2)

        # 尝试触发数据加载
        print("🔄 尝试触发gpt-oss 120B数据加载...")

        # 直接访问可能的JSON URL
        test_urls = [
            "/data/inference-performance/gpt-oss-120b-1k_1k-e2e.json",
            "/data/inference-performance/gpt-oss-120b-1k_1k-interactivity.json",
        ]

        for url in test_urls:
            try:
                # 尝试通过JavaScript访问
                script = f"""
                fetch('{url}')
                    .then(response => response.json())
                    .then(data => {{
                        window.capturedData.push({{url: '{url}', data: data}});
                        console.log('🔍 Manual fetch GPT data:', '{url}');
                    }})
                    .catch(e => console.log('❌ Manual fetch failed:', e));
                """
                driver.execute_script(script)
                time.sleep(2)
            except:
                pass

        # 等待数据加载
        time.sleep(10)

        # 获取捕获的数据
        captured_urls = driver.execute_script("return window.capturedUrls || [];")
        captured_data = driver.execute_script("return window.capturedData || [];")

        print(f"📊 捕获的URL数量: {len(captured_urls)}")
        print(f"📊 捕获的数据数量: {len(captured_data)}")

        # 分析数据
        b200_trt_found = False
        all_hwkeys = set()

        for item in captured_data:
            url = item.get('url', '')
            data = item.get('data', [])

            print(f"📄 数据URL: {url}")
            print(f"📊 数据记录数: {len(data)}")

            if isinstance(data, list) and len(data) > 0:
                for record in data:
                    hwkey = record.get('hwKey', '')
                    all_hwkeys.add(str(hwkey))
                    if 'b200_trt' in str(hwkey).lower():
                        b200_trt_found = True
                        print(f"🎯 发现b200_trt数据: {hwkey}")

                if b200_trt_found:
                    break

        print(f"📋 所有硬件类型: {sorted(list(all_hwkeys))}")
        print(f"🎯 是否发现b200_trt: {'是' if b200_trt_found else '否'}")

        return b200_trt_found

    except Exception as e:
        print(f"❌ 浏览器测试失败: {str(e)}")
        return False

    finally:
        driver.quit()

def main():
    """主函数"""
    print("🚀 开始验证InferenceMAX网站的gpt-oss 120B b200_trt数据...\n")

    print("="*60)
    print("方法1: 直接API测试")
    print("="*60)
    api_result = test_direct_api_calls()

    print("\n" + "="*60)
    print("方法2: 浏览器测试")
    print("="*60)
    browser_result = test_with_browser()

    # 总结
    print("\n" + "="*60)
    print("🎯 最终结论")
    print("="*60)

    if api_result or browser_result:
        print("✅ 在gpt-oss 120B中发现了b200_trt数据!")
        print("💡 说明网站确实有这个数据，爬虫可能需要修复")
    else:
        print("❌ 在gpt-oss 120B中未发现b200_trt数据")
        print("💡 说明网站可能确实没有这个硬件配置的数据")
        print("📊 建议检查其他模型是否有b200_trt数据进行对比")

if __name__ == "__main__":
    main()