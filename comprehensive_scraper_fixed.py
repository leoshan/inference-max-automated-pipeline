#!/usr/bin/env python3
import json
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def setup_network_monitoring(driver):
    """设置网络监控来捕获所有JSON响应"""
    script = """
    // 清除之前的监控数据
    window.capturedJsonData = [];
    window.requestCounter = 0;

    // 拦截fetch请求
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = args[0];
        const urlStr = typeof url === 'string' ? url : (url.url || '');
        const method = args[1]?.method || 'GET';

        // 只监控包含关键字的请求
        const keywords = ['api', 'data', 'benchmark', 'performance', 'model', 'hardware'];
        const shouldMonitor = keywords.some(keyword =>
            urlStr.toLowerCase().includes(keyword) ||
            urlStr.includes('.json')
        );

        if (shouldMonitor) {
            console.log('Monitoring request:', method, urlStr);
        }

        return originalFetch.apply(this, args).then(response => {
            if (shouldMonitor) {
                const contentType = response.headers.get('content-type') || '';

                if (contentType.includes('application/json')) {
                    const clonedResponse = response.clone();

                    clonedResponse.json().then(data => {
                        window.requestCounter++;
                        const requestId = window.requestCounter;

                        console.log('Captured JSON response #' + requestId, 'from:', urlStr);

                        window.capturedJsonData.push({
                            requestId: requestId,
                            url: urlStr,
                            method: method,
                            contentType: contentType,
                            data: data,
                            timestamp: Date.now(),
                            dataSize: JSON.stringify(data).length
                        });
                    }).catch(e => {
                        console.log('Failed to parse JSON from:', urlStr, e);
                    });
                }
            }

            return response;
        }).catch(e => {
            console.log('Fetch error:', e);
            return Promise.reject(e);
        });
    };

    // 拦截XMLHttpRequest
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
        this._url = url;
        this._method = method;
        return originalXHROpen.call(this, method, url, ...args);
    };

    const originalXHRSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(data) {
        const xhr = this;
        const originalOnReadyStateChange = xhr.onreadystatechange;

        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 200) {
                const url = xhr._url;
                const keywords = ['api', 'data', 'benchmark', 'performance', 'model', 'hardware'];

                if (keywords.some(keyword => url.toLowerCase().includes(keyword))) {
                    try {
                        const responseText = xhr.responseText;
                        if (responseText && responseText.trim().startsWith('{')) {
                            const jsonData = JSON.parse(responseText);

                            window.requestCounter++;
                            const requestId = window.requestCounter;

                            console.log('Captured XHR JSON response #' + requestId, 'from:', url);

                            window.capturedJsonData.push({
                                requestId: requestId,
                                url: url,
                                method: xhr._method || 'GET',
                                contentType: xhr.getResponseHeader('content-type') || 'application/json',
                                data: jsonData,
                                timestamp: Date.now(),
                                dataSize: responseText.length,
                                source: 'xhr'
                            });
                        }
                    } catch (e) {
                        console.log('Failed to parse XHR JSON from:', url, e);
                    }
                }
            }

            if (originalOnReadyStateChange) {
                originalOnReadyStateChange.call(xhr);
            }
        };

        return originalXHRSend.call(xhr, data);
    };

    console.log('Network monitoring set up');
    """

    driver.execute_script(script)

def clear_captured_data(driver):
    """清除已捕获的数据"""
    driver.execute_script("window.capturedJsonData = []; window.requestCounter = 0;")

def get_captured_data(driver):
    """获取已捕获的数据"""
    return driver.execute_script("return window.capturedJsonData || [];")

def wait_for_data_loading(driver, timeout=15, expected_min_count=1):
    """等待数据加载完成"""
    script = f"""
    return new Promise((resolve) => {{
        let attempts = 0;
        const maxAttempts = {timeout * 2}; // 每500ms检查一次

        const check = () => {{
            attempts++;
            const dataCount = window.capturedJsonData ? window.capturedJsonData.length : 0;

            if (dataCount >= {expected_min_count} || attempts >= maxAttempts) {{
                resolve({{
                    dataCount: dataCount,
                    attempts: attempts,
                    timeout: attempts >= maxAttempts
                }});
            }} else {{
                setTimeout(check, 500);
            }}
        }};

        check();
    }});
    """

    try:
        return driver.execute_script(script)
    except Exception as e:
        print(f"Error waiting for data: {e}")
        return {"dataCount": 0, "attempts": 0, "timeout": True}

def safe_click_element(driver, element, max_retries=3):
    """安全地点击元素"""
    for attempt in range(max_retries):
        try:
            # 尝试不同的点击方法
            if attempt == 0:
                element.click()
            elif attempt == 1:
                driver.execute_script("arguments[0].click();", element)
            else:
                actions = ActionChains(driver)
                actions.move_to_element(element).click().perform()

            return True
        except Exception as e:
            print(f"Click attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)

    return False

def find_and_click_dropdown(driver, button_text_pattern):
    """查找并点击包含特定文本的下拉框按钮 - 修复版本"""
    print(f"🔍 查找包含 '{button_text_pattern}' 的下拉菜单...")

    # 多种查找策略
    strategies = [
        # 策略1: 按钮文本匹配
        ('button', lambda btn: button_text_pattern.lower() in btn.text.lower()),
        # 策略2: 通过属性查找
        ('[data-testid*="select"], [data-testid*="dropdown"]', lambda el: True),
        # 策略3: 通过类名查找
        ('.model-select, .sequence-select, .select', lambda el: True),
        # 策略4: 通用下拉查找
        ('select', lambda el: True),
    ]

    for selector, condition in strategies:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    text = element.text.strip() or element.get_attribute('value') or ''
                    if condition(element) and (button_text_pattern.lower() in text.lower() or selector == 'select'):
                        print(f"✅ 找到下拉菜单: '{text}' (选择器: {selector})")
                        return safe_click_element(driver, element)
                except:
                    continue
        except:
            continue

    # 策略5: XPath查找
    try:
        xpath = f"//*[contains(text(), '{button_text_pattern}') or contains(@value, '{button_text_pattern}')]"
        elements = driver.find_elements(By.XPATH, xpath)
        for element in elements:
            if safe_click_element(driver, element):
                print(f"✅ 通过XPath找到: '{element.text}'")
                return True
    except:
        pass

    print(f"❌ 未找到包含 '{button_text_pattern}' 的下拉菜单")
    return False

def select_option_by_exact_text(driver, option_text):
    """根据精确文本选择选项 - 修复版本"""
    print(f"🎯 尝试选择选项: '{option_text}'")

    script = f"""
    const targetText = '{option_text}';
    const possibleSelectors = [
        '[role="option"]',
        'li',
        'option',
        '.option',
        '[data-option]'
    ];

    let found = false;
    let clickedElement = null;

    for (let selector of possibleSelectors) {{
        const elements = document.querySelectorAll(selector);
        console.log('检查选择器', selector, '找到', elements.length, '个元素');

        for (let element of elements) {{
            const text = element.textContent ? element.textContent.trim() : '';
            const value = element.value || '';

            console.log('选项文本:', text, '目标文本:', targetText);

            if (text === targetText ||
                text.toLowerCase() === targetText.toLowerCase() ||
                value === targetText ||
                value.toLowerCase() === targetText.toLowerCase()) {{

                try {{
                    element.click();
                    found = true;
                    clickedElement = element.tagName;
                    console.log('✅ 成功点击选项:', targetText);
                    break;
                }} catch (e) {{
                    console.log('❌ 点击选项失败:', targetText, e);
                }}
            }}
        }}

        if (found) break;
    }}

    return {{
        found: found,
        elementType: clickedElement,
        totalOptions: document.querySelectorAll(possibleSelectors.join(', ')).length
    }};
    """

    return driver.execute_script(script)

def test_combination(driver, model, sequence, combination_index):
    """测试一个特定的模型和序列组合 - 修复版本"""
    print(f"\n=== Testing Combination {combination_index}: {model} + {sequence} ===")

    # 清除之前的数据
    clear_captured_data(driver)
    time.sleep(0.5)

    # 选择模型 - 修复：传入正确的搜索文本
    print(f"Step 1: Selecting model: {model}")
    model_dropdown_clicked = find_and_click_dropdown(driver, 'Model') or find_and_click_dropdown(driver, 'model')

    if model_dropdown_clicked:
        time.sleep(1)
        model_result = select_option_by_exact_text(driver, model)

        if not model_result['found']:
            print(f"❌ Failed to select model: {model}")
            return None

        print(f"✅ Model selected successfully")
        time.sleep(3)  # 等待模型数据加载

        # 选择序列 - 修复：传入正确的搜索文本
        print(f"Step 2: Selecting sequence: {sequence}")
        sequence_dropdown_clicked = find_and_click_dropdown(driver, 'Sequence') or find_and_click_dropdown(driver, 'sequence')

        if sequence_dropdown_clicked:
            time.sleep(1)
            sequence_result = select_option_by_exact_text(driver, sequence)

            if not sequence_result['found']:
                print(f"❌ Failed to select sequence: {sequence}")
                return None

            print(f"✅ Sequence selected successfully")
            time.sleep(5)  # 等待组合数据加载

            # 获取捕获的数据
            print(f"Step 3: Capturing JSON data...")
            wait_result = wait_for_data_loading(driver, timeout=30, expected_min_count=2)
            captured_data = get_captured_data(driver)

            print(f"📊 Captured {len(captured_data)} JSON responses after {wait_result['attempts']} attempts")

            # 保存原始数据
            combination_data = {
                'combination_index': combination_index,
                'model': model,
                'sequence': sequence,
                'timestamp': time.time(),
                'capture_attempts': wait_result['attempts'],
                'data_count': len(captured_data),
                'json_responses': captured_data
            }

            return combination_data
        else:
            print(f"❌ Failed to click sequence dropdown")
            return None
    else:
        print(f"❌ Failed to click model dropdown")
        return None

def save_raw_json_files(combination_data, output_dir):
    """保存原始JSON文件"""
    model = combination_data['model'].replace(' ', '_').replace('.', '_')
    sequence = combination_data['sequence'].replace(' ', '_').replace('/', '___')
    combination_index = combination_data['combination_index']

    # 为每个JSON响应创建单独的文件
    for i, response in enumerate(combination_data['json_responses']):
        # 创建文件名：组合索引_模型_序列_响应序号.json
        filename = f"{combination_index:02d}_{model}_{sequence}_{i+1:02d}.json"
        filepath = os.path.join(output_dir, filename)

        # 保存原始JSON数据
        raw_data = {
            'metadata': {
                'combination_index': combination_index,
                'model': combination_data['model'],
                'sequence': combination_data['sequence'],
                'response_index': i + 1,
                'timestamp': combination_data['timestamp'],
                'request_id': response.get('requestId'),
                'url': response.get('url'),
                'method': response.get('method'),
                'content_type': response.get('contentType'),
                'data_size': response.get('dataSize', 0)
            },
            'data': response.get('data', [])
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved raw JSON file: {filename} ({response.get('dataSize', 0)} bytes)")

    return len(combination_data['json_responses'])

def main():
    # 定义要测试的所有组合
    models = [
        "Llama 3.3 70B Instruct",
        "gpt-oss 120B",
        "DeepSeek R1 0528"
    ]

    sequences = [
        "1K / 1K",
        "1K / 8K",
        "8K / 1K"
    ]

    # 创建输出目录
    output_dir = "json_data/raw_json_files"
    os.makedirs(output_dir, exist_ok=True)

    driver = setup_driver()

    try:
        print("🚀 Starting FIXED comprehensive InferenceMAX scraping...")
        print(f"📋 Target: {len(models)} models × {len(sequences)} sequences = {len(models) * len(sequences)} combinations")
        print(f"📁 Output directory: {output_dir}")

        # 加载页面
        print("\n📡 Loading InferenceMAX page...")
        driver.get("https://inferencemax.semianalysis.com/")
        time.sleep(5)

        # 设置网络监控
        print("🔧 Setting up network monitoring...")
        setup_network_monitoring(driver)

        # 测试所有组合
        combination_index = 1
        total_files_saved = 0
        successful_combinations = []

        for model in models:
            for sequence in sequences:
                combination_data = test_combination(driver, model, sequence, combination_index)

                if combination_data:
                    # 保存JSON文件
                    files_saved = save_raw_json_files(combination_data, output_dir)
                    total_files_saved += files_saved
                    successful_combinations.append(combination_data)
                    print(f"✅ Combination {combination_index} successful: saved {files_saved} files")
                else:
                    print(f"❌ Combination {combination_index} failed")

                combination_index += 1
                time.sleep(2)  # 组合之间的间隔

        # 生成总结报告
        print(f"\n🎉 Scraping completed!")
        print(f"📊 Successful combinations: {len(successful_combinations)}/{len(models) * len(sequences)}")
        print(f"📁 Total JSON files saved: {total_files_saved}")

        # 保存总结
        summary = {
            'timestamp': time.time(),
            'total_combinations': len(models) * len(sequences),
            'successful_combinations': len(successful_combinations),
            'total_files_saved': total_files_saved,
            'successful_combinations_data': successful_combinations
        }

        with open(os.path.join(output_dir, 'scraping_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"📋 Summary saved to: {output_dir}/scraping_summary.json")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()