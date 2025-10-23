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

        // 监控所有请求，因为API端点可能不明显
        const shouldMonitor = true; // 监控所有请求

        return originalFetch.apply(this, args).then(response => {
            const contentType = response.headers.get('content-type') || '';

            if (shouldMonitor && contentType.includes('application/json')) {
                const clonedResponse = response.clone();

                clonedResponse.json().then(data => {
                    window.requestCounter++;
                    const requestId = window.requestCounter;

                    console.log('Captured JSON response #' + requestId, 'from:', urlStr);

                    window.capturedJsonData.push({
                        requestId: requestId,
                        url: urlStr,
                        contentType: contentType,
                        data: data,
                        timestamp: Date.now(),
                        dataSize: JSON.stringify(data).length
                    });
                }).catch(e => {
                    // 忽略解析错误
                });
            }

            return response;
        }).catch(e => {
            return Promise.reject(e);
        });
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

def wait_for_data_loading(driver, timeout=20):
    """等待数据加载完成"""
    script = f"""
    return new Promise((resolve) => {{
        let attempts = 0;
        const maxAttempts = {timeout * 2};

        const check = () => {{
            attempts++;
            const dataCount = window.capturedJsonData ? window.capturedJsonData.length : 0;

            if (dataCount > 0 || attempts >= maxAttempts) {{
                resolve({{
                    dataCount: dataCount,
                    attempts: attempts
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
    except:
        return {"dataCount": 0, "attempts": 0}

def get_page_info(driver):
    """获取页面信息用于调试"""
    script = """
    const buttons = Array.from(document.querySelectorAll('button'));
    const buttonInfo = buttons.map((btn, i) => ({
        index: i,
        text: btn.textContent.trim(),
        id: btn.id,
        className: btn.className,
        ariaLabel: btn.getAttribute('aria-label')
    }));

    const selects = Array.from(document.querySelectorAll('select'));
    const selectInfo = selects.map((sel, i) => ({
        index: i,
        id: sel.id,
        className: sel.className,
        optionCount: sel.options.length
    }));

    return {
        buttons: buttonInfo,
        selects: selectInfo,
        title: document.title,
        url: window.location.href
    };
    """

    return driver.execute_script(script)

def find_model_dropdown(driver):
    """找到模型下拉框按钮"""
    script = """
    const buttons = Array.from(document.querySelectorAll('button'));

    // 寻找包含模型名称的按钮
    const modelPatterns = ['Llama', 'gpt', 'DeepSeek'];
    let modelButton = null;

    for (let button of buttons) {
        const text = button.textContent.trim();
        if (modelPatterns.some(pattern => text.includes(pattern))) {
            modelButton = button;
            break;
        }
    }

    // 如果没找到，寻找有特定属性的按钮
    if (!modelButton) {
        for (let button of buttons) {
            if (button.id && button.id.toLowerCase().includes('model')) {
                modelButton = button;
                break;
            }
        }
    }

    // 最后尝试通过class名称查找
    if (!modelButton) {
        const modelSelect = document.getElementById('model-select');
        if (modelSelect) {
            modelButton = modelSelect;
        }
    }

    return modelButton;
    """

    return driver.execute_script(script)

def find_sequence_dropdown(driver):
    """找到序列下拉框按钮"""
    script = """
    const buttons = Array.from(document.querySelectorAll('button'));

    // 寻找包含序列格式的按钮
    const sequencePatterns = ['K / K', '/'];
    let sequenceButton = null;

    for (let button of buttons) {
        const text = button.textContent.trim();
        if (sequencePatterns.some(pattern => text.includes(pattern))) {
            sequenceButton = button;
            break;
        }
    }

    // 如果没找到，寻找有特定ID的按钮
    if (!sequenceButton) {
        const sequenceSelect = document.getElementById('sequence-select');
        if (sequenceSelect) {
            sequenceButton = sequenceSelect;
        }
    }

    return sequenceButton;
    """

    return driver.execute_script(script)

def click_dropdown(driver, dropdown_element):
    """点击下拉框"""
    try:
        if dropdown_element:
            driver.execute_script("arguments[0].scrollIntoView();", dropdown_element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", dropdown_element)
            return True
    except Exception as e:
        print(f"Click dropdown failed: {e}")
        return False

    return False

def get_available_options(driver):
    """获取当前可用的选项"""
    script = """
    // 查找所有可能的选项元素
    const optionSelectors = [
        '[role="option"]',
        'li',
        'option',
        '.option'
    ];

    let allOptions = [];

    for (let selector of optionSelectors) {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
            const text = element.textContent ? element.textContent.trim() : '';
            if (text && text.length > 0 && text !== 'Reset filter') {
                allOptions.push(text);
            }
        });
    }

    // 去重
    return [...new Set(allOptions)];
    """

    return driver.execute_script(script)

def select_option(driver, option_text):
    """选择特定选项"""
    script = """
    const targetText = arguments[0];
    const optionSelectors = [
        '[role="option"]',
        'li',
        'option',
        '.option'
    ];

    for (let selector of optionSelectors) {
        const elements = document.querySelectorAll(selector);
        for (let element of elements) {
            const text = element.textContent ? element.textContent.trim() : '';
            if (text === targetText) {
                try {
                    element.click();
                    console.log('Successfully clicked option:', targetText);
                    return true;
                } catch (e) {
                    console.log('Click failed for option:', targetText, e);
                }
            }
        }
    }

    return false;
    """

    return driver.execute_script(script, option_text)

def test_combination(driver, model, sequence, combination_index):
    """测试一个特定的模型和序列组合"""
    print(f"\n=== Testing Combination {combination_index}: {model} + {sequence} ===")

    # 清除之前的数据
    clear_captured_data(driver)
    time.sleep(1)

    # 获取页面信息用于调试
    page_info = get_page_info(driver)
    print(f"Debug: Found {len(page_info['buttons'])} buttons on page")

    # 步骤1: 找到并点击模型下拉框
    print(f"Step 1: Finding model dropdown...")
    model_dropdown = find_model_dropdown(driver)

    if model_dropdown:
        print(f"Found model dropdown")
        if click_dropdown(driver, model_dropdown):
            print(f"Clicked model dropdown")
            time.sleep(1)

            # 获取可用选项
            options = get_available_options(driver)
            print(f"Available options: {options[:5]}...")  # 只显示前5个

            # 选择模型
            print(f"Selecting model: {model}")
            model_selected = select_option(driver, model)

            if model_selected:
                print(f"✅ Model selected successfully")
                time.sleep(3)  # 等待模型数据加载

                # 步骤2: 找到并点击序列下拉框
                print(f"Step 2: Finding sequence dropdown...")
                sequence_dropdown = find_sequence_dropdown(driver)

                if sequence_dropdown:
                    print(f"Found sequence dropdown")
                    if click_dropdown(driver, sequence_dropdown):
                        print(f"Clicked sequence dropdown")
                        time.sleep(1)

                        # 获取序列选项
                        sequence_options = get_available_options(driver)
                        print(f"Available sequence options: {sequence_options}")

                        # 选择序列
                        print(f"Selecting sequence: {sequence}")
                        sequence_selected = select_option(driver, sequence)

                        if sequence_selected:
                            print(f"✅ Sequence selected successfully")
                            time.sleep(4)  # 等待组合数据加载

                            # 获取捕获的数据
                            print(f"Step 3: Capturing JSON data...")
                            wait_result = wait_for_data_loading(driver, timeout=20)
                            captured_data = get_captured_data(driver)

                            print(f"📊 Captured {len(captured_data)} JSON responses")

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
                            print(f"❌ Failed to select sequence: {sequence}")
                    else:
                        print(f"❌ Failed to click sequence dropdown")
                else:
                    print(f"❌ Sequence dropdown not found")
            else:
                print(f"❌ Failed to select model: {model}")
        else:
            print(f"❌ Failed to click model dropdown")
    else:
        print(f"❌ Model dropdown not found")

    return None

def save_raw_json_files(combination_data, output_dir):
    """保存原始JSON文件"""
    model = combination_data['model'].replace(' ', '_').replace('.', '_')
    sequence = combination_data['sequence'].replace(' ', '_').replace('/', '_')
    combination_index = combination_data['combination_index']

    saved_files = 0
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
                'data_size': response.get('dataSize', 0)
            },
            'data': response.get('data', [])
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved: {filename} ({response.get('dataSize', 0)} bytes)")
        saved_files += 1

    return saved_files

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
        print("🚀 Starting fixed comprehensive InferenceMAX scraping...")
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
                    files_saved = save_raw_json_files(combination_data, output_dir)
                    total_files_saved += files_saved
                    successful_combinations.append({
                        'index': combination_index,
                        'model': model,
                        'sequence': sequence,
                        'files_saved': files_saved
                    })

                    print(f"✅ Combination {combination_index} completed: {files_saved} files saved")
                else:
                    print(f"❌ Combination {combination_index} failed")

                combination_index += 1

                # 组合之间的等待时间
                time.sleep(2)

        # 保存汇总报告
        summary = {
            'scrape_timestamp': time.time(),
            'target_combinations': len(models) * len(sequences),
            'successful_combinations': len(successful_combinations),
            'total_json_files_saved': total_files_saved,
            'models': models,
            'sequences': sequences,
            'successful_combinations_detail': successful_combinations,
            'output_directory': output_dir
        }

        summary_file = os.path.join(output_dir, 'scraping_summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n🎉 Scraping completed!")
        print(f"📊 Successful combinations: {len(successful_combinations)}/{len(models) * len(sequences)}")
        print(f"📁 Total JSON files saved: {total_files_saved}")
        print(f"📋 Summary saved to: {summary_file}")

        # 列出所有保存的文件
        saved_files = [f for f in os.listdir(output_dir) if f.endswith('.json') and f != 'scraping_summary.json']
        print(f"\n📂 Saved files ({len(saved_files)}):")
        for file in sorted(saved_files):
            print(f"  - {file}")

        return summary

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        driver.quit()

if __name__ == "__main__":
    main()