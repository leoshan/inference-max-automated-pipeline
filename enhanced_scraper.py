#!/usr/bin/env python3
"""
增强版爬虫脚本 - 专门解决gpt-oss 120B缺失b200_trt数据的问题
"""

import json
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def setup_comprehensive_network_monitoring(driver):
    """设置全面的网络监控"""
    script = """
    window.capturedJsonData = [];
    window.requestCounter = 0;
    window.capturedUrls = new Set();
    window.allNetworkRequests = [];

    // 全面的关键词匹配
    const keywords = [
        'api', 'data', 'benchmark', 'performance', 'model', 'hardware',
        'inference', 'interactivity', 'e2e', 'latency', 'throughput',
        'gpt', 'llama', 'deepseek', 'b200', 'trt', 'tensorrt', 'gpu'
    ];

    function shouldMonitorUrl(url) {
        const urlStr = url.toLowerCase();
        return keywords.some(keyword => urlStr.includes(keyword)) ||
               urlStr.includes('.json') ||
               urlStr.includes('gpt-oss') ||
               urlStr.includes('b200') ||
               urlStr.includes('tensorrt') ||
               urlStr.includes('inference-performance');
    }

    // 拦截所有网络请求
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = args[0];
        const urlStr = typeof url === 'string' ? url : (url.url || '');

        // 记录所有请求
        window.allNetworkRequests.push({
            url: urlStr,
            method: args[1]?.method || 'GET',
            timestamp: Date.now()
        });

        if (shouldMonitorUrl(urlStr)) {
            console.log('🔍 Monitoring request:', urlStr);
        }

        return originalFetch.apply(this, args).then(response => {
            if (shouldMonitorUrl(urlStr)) {
                const clonedResponse = response.clone();

                clonedResponse.json().then(data => {
                    window.requestCounter++;
                    const requestId = window.requestCounter;

                    if (!window.capturedUrls.has(urlStr)) {
                        window.capturedUrls.add(urlStr);

                        console.log('✅ Captured JSON response #' + requestId, 'from:', urlStr);

                        window.capturedJsonData.push({
                            requestId: requestId,
                            url: urlStr,
                            method: args[1]?.method || 'GET',
                            data: data,
                            timestamp: Date.now(),
                            dataSize: JSON.stringify(data).length
                        });
                    }
                }).catch(e => {
                    // 即使不是JSON也记录
                    console.log('📄 Non-JSON response from:', urlStr);
                    window.capturedJsonData.push({
                        requestId: window.requestCounter + 1,
                        url: urlStr,
                        method: args[1]?.method || 'GET',
                        data: null,
                        timestamp: Date.now(),
                        dataSize: 0,
                        nonJson: true
                    });
                });
            }

            return response;
        }).catch(e => {
            console.log('❌ Fetch error:', e);
            return Promise.reject(e);
        });
    };

    // 也拦截XMLHttpRequest
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
        this._url = url;
        this._method = method;

        window.allNetworkRequests.push({
            url: url,
            method: method,
            timestamp: Date.now(),
            type: 'XHR'
        });

        return originalXHROpen.call(this, method, url, ...args);
    };

    console.log('🚀 Comprehensive network monitoring activated');
    """

    driver.execute_script(script)

def wait_for_comprehensive_data(driver, timeout=120):
    """等待更长时间以捕获所有数据"""
    start_time = time.time()
    last_capture_count = 0
    stable_time = start_time

    print("🔍 开始全面网络监控...")

    while time.time() - start_time < timeout:
        try:
            current_data = driver.execute_script("return window.capturedJsonData || [];")
            current_count = len(current_data)
            all_requests = driver.execute_script("return window.allNetworkRequests || [];")

            if current_count > last_capture_count:
                last_capture_count = current_count
                stable_time = time.time()
                print(f"📊 已捕获 {current_count} 个JSON响应, {len(all_requests)} 个总请求")

            # 如果15秒内没有新数据，认为数据收集完成
            elif time.time() - stable_time > 15 and current_count > 0:
                print(f"✅ 数据收集稳定，共捕获 {current_count} 个JSON响应")
                break

            time.sleep(2)

        except Exception as e:
            print(f"⚠️ 监控错误: {e}")
            time.sleep(2)

    if last_capture_count == 0:
        print("⚠️ 超时：未捕获到任何JSON数据")
        return {"dataCount": 0, "attempts": 0, "timeout": True}

    print(f"🎯 成功捕获 {last_capture_count} 个JSON响应")
    return {"dataCount": last_capture_count, "attempts": 0, "timeout": False}

def comprehensive_click(driver, element, max_retries=5):
    """全面的点击方法"""
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

def find_dropdown_comprehensive(driver, search_text):
    """全面的下拉菜单查找"""
    print(f"🔍 查找包含 '{search_text}' 的控件...")

    # 尝试多种选择器和文本匹配
    strategies = [
        # CSS选择器
        ('button', lambda el: search_text.lower() in el.text.lower()),
        ('[role="button"]', lambda el: search_text.lower() in el.text.lower()),
        ('select', lambda el: search_text.lower() in el.text.lower()),
        ('option', lambda el: search_text.lower() in el.text.lower()),
        ('.dropdown', lambda el: search_text.lower() in el.text.lower()),
        ('.select', lambda el: search_text.lower() in el.text.lower()),

        # 属性匹配
        ('*[data-testid*="select"]', lambda el: True),
        ('*[data-testid*="dropdown"]', lambda el: True),
        ('*[data-test*="select"]', lambda el: True),

        # 类名匹配
        ('.model-select', lambda el: True),
        ('.hardware-select', lambda el: True),
        ('.sequence-select', lambda el: True),
    ]

    for selector, condition in strategies:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    text = element.text.strip() or element.get_attribute('value') or ''
                    aria_label = element.get_attribute('aria-label') or ''

                    full_text = (text + ' ' + aria_label).lower()

                    if search_text.lower() in full_text and condition(element):
                        print(f"✅ 找到控件: '{text}' (选择器: {selector})")
                        return comprehensive_click(driver, element)
                except:
                    continue
        except:
            continue

    # XPath查找
    try:
        xpath_conditions = [
            f"//*[contains(text(), '{search_text}')]",
            f"//*[contains(@value, '{search_text}')]",
            f"//*[contains(@aria-label, '{search_text}')]",
            f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{search_text.lower()}')]"
        ]

        for xpath in xpath_conditions:
            elements = driver.find_elements(By.XPATH, xpath)
            for element in elements:
                if comprehensive_click(driver, element):
                    return True
    except:
        pass

    print(f"❌ 未找到包含 '{search_text}' 的控件")
    return False

def select_option_comprehensive(driver, option_text):
    """全面的选项选择"""
    print(f"🎯 尝试选择选项: '{option_text}'")

    time.sleep(2)

    # 等待可能的选项加载
    for _ in range(5):
        try:
            WebDriverWait(driver, 2).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, '[role="option"], li, option')) > 0
            )
            break
        except:
            time.sleep(1)

    # 尝试多种选项选择策略
    selectors = [
        '[role="option"]',
        'li',
        'option',
        '.option',
        '[data-option]',
        '.dropdown-item',
        '[role="listbox"] > *',
        'ul > li',
        'div[role="menuitem"]',
        '.select-option'
    ]

    for selector in selectors:
        try:
            options = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"🔍 检查选择器 '{selector}': 找到 {len(options)} 个选项")

            for option in options:
                try:
                    text = option.text.strip() or ''
                    value = option.get_attribute('value') or ''
                    aria_label = option.get_attribute('aria-label') or ''

                    # 全面的文本匹配
                    full_text = (text + ' ' + value + ' ' + aria_label).lower()
                    search_text = option_text.lower()

                    if (search_text == text.lower() or
                        search_text in text.lower() or
                        search_text == value.lower() or
                        search_text in value.lower() or
                        search_text in aria_label.lower() or
                        text.lower() in search_text):  # 模糊匹配

                        print(f"✅ 匹配到选项: '{text}'")
                        return comprehensive_click(driver, option)

                except:
                    continue
        except:
            continue

    # 最后尝试JavaScript搜索和选择
    script = f"""
    const searchText = '{option_text.toLowerCase()}';
    const allElements = document.querySelectorAll('*');
    const clickableElements = [];

    for (let element of allElements) {{
        const text = element.textContent.toLowerCase().trim();
        const value = (element.value || '').toLowerCase();
        const ariaLabel = (element.getAttribute('aria-label') || '').toLowerCase();
        const role = element.getAttribute('role') || '';
        const tagName = element.tagName.toLowerCase();

        // 检查是否为可点击元素
        const isClickable = (
            role === 'option' ||
            role === 'menuitem' ||
            tagName === 'option' ||
            tagName === 'li' ||
            element.onclick ||
            element.style.cursor === 'pointer'
        );

        // 检查文本匹配
        const isMatch = (
            text === searchText ||
            text.includes(searchText) ||
            searchText.includes(text) ||
            value === searchText ||
            value.includes(searchText) ||
            ariaLabel.includes(searchText)
        );

        if (isClickable && isMatch) {{
            clickableElements.push(element);
        }}
    }}

    // 尝试点击第一个匹配的元素
    if (clickableElements.length > 0) {{
        clickableElements[0].click();
        return 'success: clicked ' + clickableElements[0].textContent.trim();
    }}

    return 'not_found';
    """

    try:
        result = driver.execute_script(script)
        if result.startswith('success'):
            print(f"✅ JavaScript成功选择: {result}")
            return True
    except Exception as e:
        print(f"⚠️ JavaScript选择失败: {e}")

    print(f"❌ 未找到选项: '{option_text}'")
    return False

def scrape_with_enhanced_method(driver, model, sequence, combo_index):
    """增强的爬取方法"""
    print(f"\n🚀 开始增强爬取组合 {combo_index}: {model} + {sequence}")

    result = {
        'combination_index': combo_index,
        'model': model,
        'sequence': sequence,
        'json_responses': [],
        'scraping_issues': [],
        'all_requests': []
    }

    try:
        print("🌐 访问网站...")
        driver.get("https://inferencemax.semianalysis.com/")

        # 等待页面完全加载
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # 额外等待React应用加载
        time.sleep(5)

        # 设置网络监控
        setup_comprehensive_network_monitoring(driver)
        time.sleep(2)

        # 模拟用户交互 - 先点击页面激活
        try:
            body = driver.find_element(By.TAG_NAME, 'body')
            body.click()
            time.sleep(1)
        except:
            pass

        # 尝试多种方法选择模型
        print(f"📝 选择模型: {model}")
        model_selectors = ["Model", "model", "Model Selection"]
        model_selected = False

        for selector in model_selectors:
            if find_dropdown_comprehensive(driver, selector):
                time.sleep(1)
                if select_option_comprehensive(driver, model):
                    model_selected = True
                    break

        if not model_selected:
            result['scraping_issues'].append("无法选择模型")
            return result

        time.sleep(3)

        # 选择序列长度
        print(f"📏 选择序列长度: {sequence}")
        sequence_selectors = ["Sequence", "sequence", "Sequence Length", "Length"]
        sequence_selected = False

        for selector in sequence_selectors:
            if find_dropdown_comprehensive(driver, selector):
                time.sleep(1)
                if select_option_comprehensive(driver, sequence):
                    sequence_selected = True
                    break

        if not sequence_selected:
            result['scraping_issues'].append("无法选择序列长度")
            return result

        time.sleep(5)

        # 等待数据加载
        print("⏳ 等待数据加载...")
        network_result = wait_for_comprehensive_data(driver, timeout=150)

        if network_result['timeout']:
            result['scraping_issues'].append("数据加载超时")
        else:
            captured_data = driver.execute_script("return window.capturedJsonData || [];")
            all_requests = driver.execute_script("return window.allNetworkRequests || [];")

            result['json_responses'] = captured_data
            result['all_requests'] = all_requests

            print(f"✅ 成功捕获 {len(captured_data)} 个JSON响应, {len(all_requests)} 个总请求")

        # 特别检查gpt-oss 120B的b200_trt数据
        if 'gpt-oss' in model.lower():
            b200_trt_count = 0
            all_hwkeys = set()

            for response in captured_data:
                data = response.get('data', [])
                if isinstance(data, list):
                    for item in data:
                        hwkey = item.get('hwKey', '')
                        all_hwkeys.add(str(hwkey))
                        if 'b200_trt' in str(hwkey).lower():
                            b200_trt_count += 1

            print(f"🔍 {model} 模型分析:")
            print(f"  所有hwKey类型: {sorted(all_hwkeys)}")
            print(f"  b200_trt数据条数: {b200_trt_count}")

            if b200_trt_count == 0 and 'b200_trt' not in str(all_hwkeys):
                result['scraping_issues'].append("网站可能没有gpt-oss 120B的b200_trt数据")

    except Exception as e:
        error_msg = f"爬取组合 {combo_index} 时出错: {str(e)}"
        print(f"❌ {error_msg}")
        result['scraping_issues'].append(error_msg)

    return result

def main():
    """主函数"""
    print("🚀 启动增强版InferenceMAX爬虫...")

    # 只测试gpt-oss 120B模型
    models = ["gpt-oss 120B"]
    sequences = ["1K / 1K", "1K / 8K", "8K / 1K"]

    # 创建输出目录
    output_dir = "json_data/raw_json_files"
    os.makedirs(output_dir, exist_ok=True)

    # 设置驱动
    driver = setup_driver()
    success_count = 0
    issue_count = 0

    try:
        combo_index = 4  # 从4开始，对应原脚本的gpt-oss开始编号

        for model in models:
            for sequence in sequences:
                print(f"\n{'='*80}")
                print(f"📊 处理组合 {combo_index}: {model} + {sequence}")
                print(f"{'='*80}")

                result = scrape_with_enhanced_method(driver, model, sequence, combo_index)

                if result['json_responses']:
                    # 保存数据
                    for i, response in enumerate(result['json_responses']):
                        data = response.get('data', [])
                        if not data:
                            continue

                        try:
                            file_data = {
                                'metadata': {
                                    'combination_index': combo_index,
                                    'model': model,
                                    'sequence': sequence,
                                    'response_index': i + 1,
                                    'timestamp': response.get('timestamp', time.time()),
                                    'request_id': response.get('requestId', i + 1),
                                    'url': response.get('url', ''),
                                    'data_size': response.get('dataSize', 0)
                                },
                                'data': data
                            }

                            model_safe = model.replace(' ', '_').replace('.', '_')
                            sequence_safe = sequence.replace(' ', '_').replace('/', '___')
                            filename = f"{combo_index:02d}_{model_safe}_{sequence_safe}_{i+1:02d}.json"
                            file_path = os.path.join(output_dir, filename)

                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(file_data, f, ensure_ascii=False, indent=2)

                            print(f"💾 保存文件: {filename} ({len(data)} 条数据)")

                        except Exception as e:
                            print(f"❌ 保存响应 {i+1} 失败: {str(e)}")

                    success_count += 1
                else:
                    issue_count += 1

                # 显示问题和网络请求
                if result['scraping_issues']:
                    print(f"⚠️ 发现问题:")
                    for issue in result['scraping_issues']:
                        print(f"  - {issue}")

                if result['all_requests']:
                    print(f"🌐 捕获到 {len(result['all_requests'])} 个网络请求")
                    # 显示前10个请求URL
                    for i, req in enumerate(result['all_requests'][:10]):
                        print(f"  {i+1}. {req['url']}")

                combo_index += 1
                time.sleep(3)

    finally:
        driver.quit()

    print(f"\n{'='*80}")
    print("📈 爬取统计:")
    print(f"{'='*80}")
    print(f"成功组合: {success_count}")
    print(f"问题组合: {issue_count}")

if __name__ == "__main__":
    main()