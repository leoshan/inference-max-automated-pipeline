#!/usr/bin/env python3
"""
测试修复后的爬虫脚本 - 只测试gpt-oss 120B模型
"""

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
        const keywords = ['api', 'data', 'benchmark', 'performance', 'model', 'hardware', 'inference-performance'];
        const shouldMonitor = keywords.some(keyword =>
            urlStr.toLowerCase().includes(keyword) ||
            urlStr.includes('.json') ||
            urlStr.includes('gpt-oss') ||
            urlStr.includes('b200')
        );

        if (shouldMonitor) {
            console.log('🔍 Monitoring request:', method, urlStr);
        }

        return originalFetch.apply(this, args).then(response => {
            if (shouldMonitor) {
                const contentType = response.headers.get('content-type') || '';

                if (contentType.includes('application/json')) {
                    const clonedResponse = response.clone();

                    clonedResponse.json().then(data => {
                        window.requestCounter++;
                        const requestId = window.requestCounter;

                        console.log('✅ Captured JSON response #' + requestId, 'from:', urlStr);

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
                        console.log('❌ Failed to parse JSON from:', urlStr, e);
                    });
                }
            }

            return response;
        }).catch(e => {
            console.log('❌ Fetch error:', e);
            return Promise.reject(e);
        });
    };

    console.log('🚀 Enhanced network monitoring activated');
    """

    driver.execute_script(script)

def clear_captured_data(driver):
    """清除已捕获的数据"""
    driver.execute_script("window.capturedJsonData = []; window.requestCounter = 0;")

def get_captured_data(driver):
    """获取已捕获的数据"""
    return driver.execute_script("return window.capturedJsonData || [];")

def wait_for_data_loading(driver, timeout=60, expected_min_count=2):
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

def safe_click_element(driver, element, max_retries=5):
    """安全地点击元素"""
    for attempt in range(max_retries):
        try:
            WebDriverWait(driver, 10).until(EC.visibility_of(element))
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(element))

            if attempt == 0:
                element.click()
            elif attempt == 1:
                driver.execute_script("arguments[0].click();", element)
            elif attempt == 2:
                actions = ActionChains(driver)
                actions.move_to_element(element).click().perform()
            elif attempt == 3:
                driver.execute_script("""
                    var element = arguments[0];
                    var event = new MouseEvent('click', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true
                    });
                    element.dispatchEvent(event);
                """, element)
            else:
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)
                element.click()

            print(f"✅ 点击成功 (尝试 {attempt + 1})")
            return True

        except Exception as e:
            print(f"⚠️ 点击尝试 {attempt + 1} 失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)

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
    """根据精确文本选择选项 - 增强版本"""
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
    let allOptions = [];

    for (let selector of possibleSelectors) {{
        const elements = document.querySelectorAll(selector);
        console.log('🔍 检查选择器', selector, '找到', elements.length, '个元素');

        for (let element of elements) {{
            const text = element.textContent ? element.textContent.trim() : '';
            const value = element.value || '';
            const ariaLabel = element.getAttribute('aria-label') || '';

            allOptions.push(text || value || ariaLabel);

            // 增强的文本匹配
            if (text === targetText ||
                text.toLowerCase() === targetText.toLowerCase() ||
                value === targetText ||
                value.toLowerCase() === targetText.toLowerCase() ||
                ariaLabel.includes(targetText) ||
                text.includes(targetText) ||
                targetText.includes(text)) {{

                try {{
                    element.click();
                    found = true;
                    clickedElement = element.tagName;
                    console.log('✅ 成功点击选项:', targetText, '实际文本:', text);
                    break;
                }} catch (e) {{
                    console.log('❌ 点击选项失败:', targetText, e);
                }}
            }}
        }}

        if (found) break;
    }}

    console.log('📋 所有可用选项:', allOptions);

    return {{
        found: found,
        elementType: clickedElement,
        totalOptions: allOptions.length,
        availableOptions: allOptions
    }};
    """

    return driver.execute_script(script)

def test_gpt_combination(driver, model, sequence, combination_index):
    """测试gpt-oss 120B模型组合"""
    print(f"\n{'='*80}")
    print(f"🔍 Testing Combination {combination_index}: {model} + {sequence}")
    print(f"{'='*80}")

    # 清除之前的数据
    clear_captured_data(driver)
    time.sleep(1)

    try:
        # 访问网站
        print("🌐 访问InferenceMAX网站...")
        driver.get("https://inferencemax.semianalysis.com/")
        time.sleep(5)

        # 设置网络监控
        setup_network_monitoring(driver)
        time.sleep(2)

        # 选择模型 - 修复：传入正确的搜索文本
        print(f"📝 Step 1: 选择模型: {model}")
        model_dropdown_clicked = find_and_click_dropdown(driver, 'Model') or find_and_click_dropdown(driver, 'model')

        if model_dropdown_clicked:
            time.sleep(2)
            model_result = select_option_by_exact_text(driver, model)

            if not model_result['found']:
                print(f"❌ 模型选择失败: {model}")
                print(f"📋 可用选项: {model_result.get('availableOptions', [])}")
                return None

            print(f"✅ 模型选择成功")
            time.sleep(4)  # 等待模型数据加载

            # 选择序列 - 修复：传入正确的搜索文本
            print(f"📏 Step 2: 选择序列长度: {sequence}")
            sequence_dropdown_clicked = find_and_click_dropdown(driver, 'Sequence') or find_and_click_dropdown(driver, 'sequence')

            if sequence_dropdown_clicked:
                time.sleep(2)
                sequence_result = select_option_by_exact_text(driver, sequence)

                if not sequence_result['found']:
                    print(f"❌ 序列长度选择失败: {sequence}")
                    print(f"📋 可用选项: {sequence_result.get('availableOptions', [])}")
                    return None

                print(f"✅ 序列长度选择成功")
                time.sleep(6)  # 等待组合数据加载

                # 获取捕获的数据
                print(f"⏳ Step 3: 捕获JSON数据...")
                wait_result = wait_for_data_loading(driver, timeout=90, expected_min_count=2)
                captured_data = get_captured_data(driver)

                print(f"📊 捕获到 {len(captured_data)} 个JSON响应 (尝试 {wait_result['attempts']} 次)")

                # 分析捕获的数据
                gpt_b200_trt_count = 0
                all_hwkeys = set()
                gpt_data_count = 0

                for response in captured_data:
                    url = response.get('url', '')
                    data = response.get('data', [])

                    # 检查是否是gpt-oss相关数据
                    if 'gpt-oss' in url.lower():
                        gpt_data_count += 1
                        print(f"  📄 GPT相关响应: {url}")

                        if isinstance(data, list):
                            for item in data:
                                hwkey = item.get('hwKey', '')
                                all_hwkeys.add(str(hwkey))
                                if 'b200_trt' in str(hwkey).lower():
                                    gpt_b200_trt_count += 1

                print(f"\n🔍 {model} 数据分析:")
                print(f"  GPT相关响应数: {gpt_data_count}")
                print(f"  所有hwKey类型: {sorted(all_hwkeys)}")
                print(f"  b200_trt数据条数: {gpt_b200_trt_count}")

                # 保存组合数据
                combination_data = {
                    'combination_index': combination_index,
                    'model': model,
                    'sequence': sequence,
                    'timestamp': time.time(),
                    'capture_attempts': wait_result['attempts'],
                    'data_count': len(captured_data),
                    'gpt_data_count': gpt_data_count,
                    'b200_trt_count': gpt_b200_trt_count,
                    'all_hwkeys': sorted(all_hwkeys),
                    'json_responses': captured_data
                }

                return combination_data
            else:
                print(f"❌ 序列长度下拉菜单点击失败")
                return None
        else:
            print(f"❌ 模型下拉菜单点击失败")
            return None

    except Exception as e:
        error_msg = f"测试组合 {combination_index} 时出错: {str(e)}"
        print(f"❌ {error_msg}")
        return None

def main():
    """主函数 - 只测试gpt-oss 120B模型"""
    print("🚀 启动修复版GPT-OSS 120B数据采集测试...")

    # 只测试gpt-oss 120B模型
    model = "gpt-oss 120B"
    sequences = ["1K / 1K", "1K / 8K", "8K / 1K"]

    # 创建输出目录
    output_dir = "json_data/raw_json_files"
    os.makedirs(output_dir, exist_ok=True)

    driver = setup_driver()

    try:
        print(f"📋 测试目标: {model} × {len(sequences)} 序列")
        print(f"📁 输出目录: {output_dir}")

        successful_combinations = []
        total_b200_trt_found = 0

        for i, sequence in enumerate(sequences, 1):
            combination_data = test_gpt_combination(driver, model, sequence, i)

            if combination_data:
                successful_combinations.append(combination_data)
                total_b200_trt_found += combination_data['b200_trt_count']
                print(f"✅ 组合 {i} 成功: 发现 {combination_data['b200_trt_count']} 条b200_trt数据")
            else:
                print(f"❌ 组合 {i} 失败")

            time.sleep(3)  # 组合之间的间隔

        # 生成总结报告
        print(f"\n{'='*80}")
        print(f"📈 GPT-OSS 120B 测试统计:")
        print(f"{'='*80}")
        print(f"成功组合: {len(successful_combinations)}/{len(sequences)}")
        print(f"总共发现的b200_trt数据: {total_b200_trt_found}")

        if total_b200_trt_found == 0:
            print(f"\n❌ 关键发现: gpt-oss 120B模型确实没有b200_trt硬件配置数据")
            print(f"🌐 建议手动访问网站确认")
        else:
            print(f"\n✅ 成功发现b200_trt数据! 爬虫修复有效")

        # 保存测试结果
        test_results = {
            'timestamp': time.time(),
            'model': model,
            'sequences_tested': sequences,
            'successful_combinations': len(successful_combinations),
            'total_b200_trt_found': total_b200_trt_found,
            'combination_results': successful_combinations
        }

        with open(os.path.join(output_dir, 'gpt_test_results.json'), 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        print(f"📋 测试结果已保存: {output_dir}/gpt_test_results.json")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()