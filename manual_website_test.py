#!/usr/bin/env python3
"""
手动访问InferenceMAX网站并检查gpt-oss 120B的b200_trt数据
"""

import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def setup_comprehensive_monitoring(driver):
    """设置全面的网络监控"""
    script = """
    window.allJsonData = [];
    window.requestCounter = 0;

    // 拦截所有网络请求
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = args[0];
        const urlStr = typeof url === 'string' ? url : (url.url || '');

        // 监控所有JSON请求
        return originalFetch.apply(this, args).then(response => {
            const clonedResponse = response.clone();
            const contentType = response.headers.get('content-type') || '';

            if (contentType.includes('application/json')) {
                clonedResponse.json().then(data => {
                    window.requestCounter++;
                    const requestId = window.requestCounter;

                    console.log('🔍 Captured JSON #' + requestId, 'URL:', urlStr);

                    window.allJsonData.push({
                        requestId: requestId,
                        url: urlStr,
                        method: args[1]?.method || 'GET',
                        data: data,
                        timestamp: Date.now(),
                        dataSize: JSON.stringify(data).length
                    });
                }).catch(e => {
                    console.log('❌ JSON parse error:', urlStr, e);
                });
            }

            return response;
        }).catch(e => {
            console.log('❌ Fetch error:', e);
            return Promise.reject(e);
        });
    };

    // 也拦截XHR
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
        this._url = url;
        this._method = method;

        const originalXHRSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.send = function(data) {
            const xhr = this;
            const originalOnReadyStateChange = xhr.onreadystatechange;

            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    try {
                        const responseText = xhr.responseText;
                        if (responseText && responseText.trim().startsWith('{')) {
                            const jsonData = JSON.parse(responseText);

                            window.requestCounter++;
                            const requestId = window.requestCounter;

                            console.log('🔍 Captured XHR JSON #' + requestId, 'URL:', xhr._url);

                            window.allJsonData.push({
                                requestId: requestId,
                                url: xhr._url,
                                method: xhr._method || 'GET',
                                data: jsonData,
                                timestamp: Date.now(),
                                dataSize: responseText.length,
                                source: 'xhr'
                            });
                        }
                    } catch (e) {
                        console.log('❌ XHR JSON parse error:', xhr._url, e);
                    }
                }

                if (originalOnReadyStateChange) {
                    originalOnReadyStateChange.call(xhr);
                }
            };

            return originalXHRSend.call(xhr, data);
        };

        return originalXHROpen.call(this, method, url, ...args);
    };

    console.log('🚀 Comprehensive network monitoring setup complete');
    """

    driver.execute_script(script)

def wait_and_capture_data(driver, timeout=30):
    """等待并捕获数据"""
    print("⏳ 等待数据加载...")
    time.sleep(timeout)

    captured_data = driver.execute_script("return window.allJsonData || [];")
    print(f"📊 捕获到 {len(captured_data)} 个JSON响应")

    return captured_data

def analyze_gpt_b200_data(captured_data):
    """分析gpt-oss 120B的b200_trt数据"""
    print(f"\n🔍 分析捕获的数据...")

    gpt_related_responses = []
    b200_trt_count = 0
    all_hwkeys = set()

    for response in captured_data:
        url = response.get('url', '').lower()
        data = response.get('data', [])

        # 检查是否是gpt-oss相关的响应
        if 'gpt-oss' in url:
            gpt_related_responses.append(response)
            print(f"  📄 GPT-OSS相关URL: {url}")

            if isinstance(data, list):
                for item in data:
                    hwkey = item.get('hwKey', '')
                    all_hwkeys.add(str(hwkey))
                    if 'b200_trt' in str(hwkey).lower():
                        b200_trt_count += 1
                        print(f"  🎯 发现b200_trt数据: {hwkey}")

    print(f"\n📈 分析结果:")
    print(f"  GPT-OSS相关响应数: {len(gpt_related_responses)}")
    print(f"  所有hwKey类型: {sorted(all_hwkeys)}")
    print(f"  b200_trt数据条数: {b200_trt_count}")

    return {
        'gpt_responses': gpt_related_responses,
        'b200_trt_count': b200_trt_count,
        'all_hwkeys': all_hwkeys
    }

def main():
    """主函数"""
    print("🚀 开始手动验证InferenceMAX网站的gpt-oss 120B数据...")

    driver = setup_driver()

    try:
        # 访问网站
        print("🌐 访问 https://inferencemax.semianalysis.com/")
        driver.get("https://inferencemax.semianalysis.com/")
        time.sleep(5)

        # 设置网络监控
        print("🔧 设置网络监控...")
        setup_comprehensive_monitoring(driver)
        time.sleep(2)

        # 模拟用户交互步骤
        print("📝 Step 1: 选择 gpt-oss 120B 模型")

        # 尝试多种方法选择模型
        model_select_attempts = [
            # 方法1: 尝试点击包含Model的按钮
            lambda: driver.find_element(By.XPATH, "//*[contains(text(), 'Model')]"),
            # 方法2: 尝试查找select元素
            lambda: driver.find_element(By.CSS_SELECTOR, "select"),
            # 方法3: 尝试查找包含Model的任何可点击元素
            lambda: driver.find_element(By.XPATH, "//*[contains(text(), 'Model') or contains(@value, 'Model')]"),
        ]

        model_selected = False
        for i, attempt_func in enumerate(model_select_attempts):
            try:
                print(f"  🎯 尝试方法 {i+1} 选择模型...")
                element = attempt_func()
                driver.execute_script("arguments[0].click();", element)
                time.sleep(2)

                # 尝试选择gpt-oss 120B
                gpt_option = driver.find_element(By.XPATH, "//*[contains(text(), 'gpt-oss 120B')]")
                driver.execute_script("arguments[0].click();", gpt_option)

                print("  ✅ 模型选择成功")
                model_selected = True
                time.sleep(3)
                break

            except Exception as e:
                print(f"  ⚠️ 方法 {i+1} 失败: {e}")
                continue

        if not model_selected:
            print("❌ 无法选择模型，将等待页面自动加载所有数据")

        # 等待数据加载
        print("⏳ 等待页面数据加载...")
        time.sleep(10)

        # 模拟选择ISL/OSL为1K/1K
        print("📏 Step 2: 选择ISL/OSL为1K/1K")

        sequence_attempts = [
            lambda: driver.find_element(By.XPATH, "//*[contains(text(), 'Sequence')]"),
            lambda: driver.find_element(By.XPATH, "//*[contains(text(), '1K') or contains(text(), '1k')]"),
            lambda: driver.find_element(By.CSS_SELECTOR, "select:not(:first-child)"),
        ]

        sequence_selected = False
        for i, attempt_func in enumerate(sequence_attempts):
            try:
                print(f"  🎯 尝试方法 {i+1} 选择序列...")
                element = attempt_func()
                driver.execute_script("arguments[0].click();", element)
                time.sleep(2)

                # 尝试选择1K/1K
                sequence_option = driver.find_element(By.XPATH, "//*[contains(text(), '1K / 1K') or contains(text(), '1K/1K') or contains(text(), '1k/1k')]")
                driver.execute_script("arguments[0].click();", sequence_option)

                print("  ✅ 序列选择成功")
                sequence_selected = True
                time.sleep(3)
                break

            except Exception as e:
                print(f"  ⚠️ 序列选择方法 {i+1} 失败: {e}")
                continue

        if not sequence_selected:
            print("❌ 无法选择序列，继续等待数据加载")

        # 额外等待以确保所有数据加载完成
        print("⏳ 额外等待数据加载...")
        time.sleep(15)

        # 捕获所有数据
        captured_data = wait_and_capture_data(driver, timeout=30)

        # 分析数据
        analysis_result = analyze_gpt_b200_data(captured_data)

        # 保存结果
        result = {
            'timestamp': time.time(),
            'model_selected': model_selected,
            'sequence_selected': sequence_selected,
            'total_responses': len(captured_data),
            'analysis': analysis_result,
            'all_responses': captured_data
        }

        with open('manual_website_test_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n🎯 最终结论:")
        if analysis_result['b200_trt_count'] > 0:
            print(f"✅ 在gpt-oss 120B数据中发现 {analysis_result['b200_trt_count']} 条b200_trt数据!")
            print(f"💡 网站确实有这个数据，爬虫可能有问题")
        else:
            print(f"❌ 在gpt-oss 120B数据中未发现任何b200_trt数据")
            print(f"📋 发现的硬件类型: {sorted(analysis_result['all_hwkeys'])}")
            print(f"💡 网站可能确实没有这个数据组合")

        print(f"\n📄 详细结果已保存到: manual_website_test_result.json")

    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()