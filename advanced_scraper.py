#!/usr/bin/env python3
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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

def execute_with_retry(driver, script, max_retries=3):
    """执行JavaScript并重试"""
    for attempt in range(max_retries):
        try:
            return driver.execute_script(script)
        except Exception as e:
            print(f"Script execution attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise e

def setup_network_monitoring(driver):
    """设置网络监控"""
    script = """
    // 设置网络请求拦截
    window.capturedData = [];
    const originalFetch = window.fetch;
    const originalXHROpen = XMLHttpRequest.prototype.open;
    const originalXHRSend = XMLHttpRequest.prototype.send;

    // 拦截fetch请求
    window.fetch = function(...args) {
        const url = args[0];
        const urlStr = typeof url === 'string' ? url : (url.url || '');

        // 检查是否是API请求
        if (urlStr.includes('api') || urlStr.includes('data') || urlStr.includes('json')) {
            console.log('Fetch API call:', urlStr);

            return originalFetch.apply(this, args).then(response => {
                const clonedResponse = response.clone();

                // 尝试解析JSON响应
                if (response.headers.get('content-type')?.includes('application/json')) {
                    clonedResponse.json().then(data => {
                        window.capturedData.push({
                            type: 'fetch',
                            url: urlStr,
                            data: data,
                            timestamp: Date.now()
                        });
                        console.log('Captured JSON data:', data);
                    }).catch(e => console.log('Failed to parse JSON:', e));
                }

                return response;
            }).catch(e => {
                console.log('Fetch error:', e);
                return Promise.reject(e);
            });
        }

        return originalFetch.apply(this, args);
    };

    // 拦截XMLHttpRequest
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
        this._url = url;
        if (url.includes('api') || url.includes('data') || url.includes('json')) {
            console.log('XHR request:', method, url);
        }
        return originalXHROpen.call(this, method, url, ...args);
    };

    XMLHttpRequest.prototype.send = function(data) {
        const xhr = this;
        const originalOnReadyStateChange = xhr.onreadystatechange;

        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 200) {
                if (xhr._url && (xhr._url.includes('api') || xhr._url.includes('data') || xhr._url.includes('json'))) {
                    try {
                        const responseText = xhr.responseText;
                        if (responseText && responseText.trim().startsWith('{')) {
                            const jsonData = JSON.parse(responseText);
                            window.capturedData.push({
                                type: 'xhr',
                                url: xhr._url,
                                data: jsonData,
                                timestamp: Date.now()
                            });
                            console.log('Captured XHR JSON data:', jsonData);
                        }
                    } catch (e) {
                        console.log('Failed to parse XHR JSON:', e);
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

    execute_with_retry(driver, script)

def click_element_safely(driver, element):
    """安全地点击元素"""
    try:
        # 尝试直接点击
        element.click()
        return True
    except Exception as e:
        try:
            # 尝试使用JavaScript点击
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e2:
            try:
                # 尝试使用ActionChains
                actions = ActionChains(driver)
                actions.move_to_element(element).click().perform()
                return True
            except Exception as e3:
                print(f"All click methods failed: {e}, {e2}, {e3}")
                return False

def get_dropdown_options_enhanced(driver, dropdown_id):
    """增强的下拉框选项获取"""
    script = f"""
    const dropdown = document.getElementById('{dropdown_id}');
    if (!dropdown) {{
        console.log('Dropdown not found: {dropdown_id}');
        return [];
    }}

    // 点击打开下拉框
    dropdown.click();

    // 等待选项出现
    setTimeout(() => {{
        const options = document.querySelectorAll('[role="option"], li, option');
        const optionTexts = [];

        options.forEach(option => {{
            const text = option.textContent?.trim();
            if (text && text !== 'Reset filter' && text.length > 0) {{
                optionTexts.push(text);
            }}
        }});

        console.log('Found options:', optionTexts);
        window.lastDropdownOptions = optionTexts;

        // 关闭下拉框
        dropdown.click();
    }}, 500);

    return 'waiting';
    """

    try:
        result = execute_with_retry(driver, script)
        time.sleep(1)  # 等待执行完成

        # 获取结果
        options = execute_with_retry(driver, "return window.lastDropdownOptions || [];")
        return options
    except Exception as e:
        print(f"Error getting dropdown options: {e}")
        return []

def select_dropdown_option(driver, dropdown_id, option_text):
    """选择下拉框选项"""
    script = f"""
    const dropdown = document.getElementById('{dropdown_id}');
    if (!dropdown) {{
        console.log('Dropdown not found: {dropdown_id}');
        return false;
    }}

    // 点击打开下拉框
    dropdown.click();

    setTimeout(() => {{
        const options = document.querySelectorAll('[role="option"], li, option');
        let found = false;

        options.forEach(option => {{
            const text = option.textContent?.trim();
            if (text === '{option_text}') {{
                option.click();
                found = true;
                console.log('Selected option:', text);
            }}
        }});

        if (!found) {{
            console.log('Option not found:', '{option_text}');
        }}

        window.lastSelectionResult = found;
    }}, 500);

    return 'waiting';
    """

    try:
        result = execute_with_retry(driver, script)
        time.sleep(1)  # 等待执行完成

        # 获取结果
        success = execute_with_retry(driver, "return window.lastSelectionResult || false;")
        return success
    except Exception as e:
        print(f"Error selecting dropdown option: {e}")
        return False

def wait_for_data_loading(driver, timeout=10):
    """等待数据加载完成"""
    script = """
    return new Promise((resolve) => {
        let checkCount = 0;
        const maxChecks = 20;

        const checkData = () => {
            checkCount++;

            // 检查是否有新的数据加载
            const dataCount = window.capturedData ? window.capturedData.length : 0;

            if (dataCount > 0 || checkCount >= maxChecks) {
                resolve(dataCount);
            } else {
                setTimeout(checkData, 500);
            }
        };

        checkData();
    });
    """

    try:
        return execute_with_retry(driver, script)
    except Exception as e:
        print(f"Error waiting for data loading: {e}")
        return 0

def main():
    driver = setup_driver()

    try:
        print("Loading page...")
        driver.get("https://inferencemax.semianalysis.com/")
        time.sleep(5)

        # 设置网络监控
        print("Setting up network monitoring...")
        setup_network_monitoring(driver)

        # 获取初始数据
        model_options = get_dropdown_options_enhanced(driver, 'model-select')
        sequence_options = get_dropdown_options_enhanced(driver, 'sequence-select')

        print(f"Model options: {model_options}")
        print(f"Sequence options: {sequence_options}")

        # 过滤有效选项
        valid_models = [opt for opt in model_options if opt and 'Reset' not in opt]
        valid_sequences = [opt for opt in sequence_options if opt and 'Reset' not in opt]

        print(f"Valid models: {valid_models}")
        print(f"Valid sequences: {valid_sequences}")

        # 测试不同的组合
        all_combinations = []

        for i, model in enumerate(valid_models[:3]):  # 限制为前3个模型
            for j, sequence in enumerate(valid_sequences[:3]):  # 限制为前3个序列
                print(f"\nTesting combination {i+1}-{j+1}: {model} + {sequence}")

                # 选择模型
                print(f"Selecting model: {model}")
                model_success = select_dropdown_option(driver, 'model-select', model)

                if model_success:
                    time.sleep(1)  # 等待数据加载

                    # 选择序列
                    print(f"Selecting sequence: {sequence}")
                    sequence_success = select_dropdown_option(driver, 'sequence-select', sequence)

                    if sequence_success:
                        time.sleep(2)  # 等待数据加载

                        # 等待并获取数据
                        data_count = wait_for_data_loading(driver)

                        # 保存当前组合的数据
                        current_data = {
                            'combination_id': f"{model}_{sequence}",
                            'model': model,
                            'sequence': sequence,
                            'timestamp': time.time(),
                            'data_count': data_count,
                            'captured_data': execute_with_retry(driver, "return window.capturedData || [];")
                        }

                        all_combinations.append(current_data)
                        print(f"Captured {data_count} data items for this combination")

                # 重置页面状态
                time.sleep(1)

        # 保存所有数据
        result = {
            'timestamp': time.time(),
            'url': driver.current_url,
            'title': driver.title,
            'model_options': valid_models,
            'sequence_options': valid_sequences,
            'combinations': all_combinations,
            'total_combinations_tested': len(all_combinations)
        }

        # 保存到文件
        with open('json_data/inference_max_detailed_data.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\nData saved to json_data/inference_max_detailed_data.json")
        print(f"Total combinations tested: {len(all_combinations)}")

        # 保存单独的组合数据文件
        for combo in all_combinations:
            if combo['captured_data']:
                filename = f"json_data/combo_{combo['combination_id'].replace('/', '_').replace(' ', '_')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(combo, f, indent=2, ensure_ascii=False)
                print(f"Saved combination data to: {filename}")

        return result

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()