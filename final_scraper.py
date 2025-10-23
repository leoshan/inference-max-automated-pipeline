#!/usr/bin/env python3
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def setup_network_interception(driver):
    """设置网络拦截来捕获JSON数据"""
    script = """
    // 拦截所有网络请求
    window.jsonResponses = [];

    // 拦截fetch
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = args[0];
        const urlStr = typeof url === 'string' ? url : (url.url || '');

        return originalFetch.apply(this, args).then(response => {
            // 克隆响应以便读取
            const clonedResponse = response.clone();

            // 检查响应类型
            const contentType = response.headers.get('content-type') || '';

            if (contentType.includes('application/json') ||
                urlStr.includes('api') ||
                urlStr.includes('data') ||
                urlStr.includes('benchmark')) {

                clonedResponse.json().then(data => {
                    console.log('Captured JSON from:', urlStr);
                    window.jsonResponses.push({
                        url: urlStr,
                        method: args[1]?.method || 'GET',
                        data: data,
                        timestamp: Date.now(),
                        contentType: contentType
                    });
                }).catch(e => {
                    console.log('Failed to parse JSON from:', urlStr, e);
                });
            }

            return response;
        });
    };

    console.log('Network interception set up');
    """

    driver.execute_script(script)

def click_and_wait(driver, element, wait_time=1):
    """点击元素并等待"""
    try:
        # 使用JavaScript点击
        driver.execute_script("arguments[0].click();", element)
        time.sleep(wait_time)
        return True
    except Exception as e:
        print(f"Click failed: {e}")
        return False

def get_options_by_text_pattern(driver, patterns):
    """根据文本模式获取选项"""
    script = f"""
    const patterns = {json.dumps(patterns)};
    const allOptions = [];

    // 查找所有可能的选项元素
    const optionElements = document.querySelectorAll('[role="option"], li, option, .option');

    optionElements.forEach(element => {{
        const text = element.textContent?.trim() || '';

        // 检查是否匹配任何模式
        const matched = patterns.some(pattern => {{
            if (typeof pattern === 'string') {{
                return text.includes(pattern);
            }} else if (typeof pattern === 'object') {{
                return pattern.regex && new RegExp(pattern.regex).test(text);
            }}
            return false;
        }});

        if (matched && text && text.length > 0) {{
            allOptions.push(text);
        }}
    }});

    // 去重并返回
    return [...new Set(allOptions)];
    """

    return driver.execute_script(script)

def select_option_by_text(driver, text):
    """根据文本选择选项"""
    script = f"""
    const targetText = '{text}';
    const optionElements = document.querySelectorAll('[role="option"], li, option, .option');
    let found = false;

    optionElements.forEach(element => {{
        const elementText = element.textContent?.trim() || '';
        if (elementText === targetText) {{
            try {{
                element.click();
                found = true;
                console.log('Selected:', targetText);
            }} catch (e) {{
                console.log('Click failed for:', targetText, e);
            }}
        }}
    }});

    return found;
    """

    return driver.execute_script(script)

def wait_for_json_data(driver, timeout=10):
    """等待JSON数据加载"""
    script = """
    return new Promise((resolve) => {
        let attempts = 0;
        const maxAttempts = 20;

        const check = () => {
            attempts++;
            const dataCount = window.jsonResponses ? window.jsonResponses.length : 0;

            if (dataCount > 0 || attempts >= maxAttempts) {
                resolve(dataCount);
            } else {
                setTimeout(check, 500);
            }
        };

        check();
    });
    """

    try:
        return driver.execute_script(script)
    except:
        return 0

def main():
    driver = setup_driver()

    try:
        print("Loading InferenceMAX page...")
        driver.get("https://inferencemax.semianalysis.com/")
        time.sleep(5)

        # 设置网络拦截
        print("Setting up network interception...")
        setup_network_interception(driver)

        # 定义模型和序列的模式
        model_patterns = [
            "Llama", "gpt", "DeepSeek", "claude", "mixtral", "llama"
        ]

        sequence_patterns = [
            {"regex": r"\d+K\s*/\s*\d+K"},  # 匹配 "1K / 1K", "1K / 8K" 等
            {"regex": r"\d+\s*/\s*\d+"}     # 匹配其他数字/数字格式
        ]

        # 获取页面上的所有选项
        print("Finding model options...")
        model_options = get_options_by_text_pattern(driver, model_patterns)

        print("Finding sequence options...")
        sequence_options = get_options_by_text_pattern(driver, sequence_patterns)

        print(f"Found model options: {model_options}")
        print(f"Found sequence options: {sequence_options}")

        # 如果没有找到，尝试打开下拉框
        if not model_options or not sequence_options:
            print("Trying to open dropdowns...")

            # 尝试找到并点击下拉框按钮
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            print(f"Found {len(buttons)} buttons")

            for i, button in enumerate(buttons):
                text = button.text.strip()
                print(f"Button {i}: {text}")

                if text and not text.startswith('Token') and 'Reset' not in text:
                    print(f"Clicking button: {text}")
                    if click_and_wait(driver, button):
                        # 获取新出现的选项
                        new_options = get_options_by_text_pattern(driver, model_patterns + sequence_patterns)
                        print(f"New options after clicking: {new_options}")

            # 重新获取选项
            model_options = get_options_by_text_pattern(driver, model_patterns)
            sequence_options = get_options_by_text_pattern(driver, sequence_patterns)

        # 过滤并准备测试组合
        valid_models = [opt for opt in model_options if any(pattern in opt.lower() for pattern in ['llama', 'gpt', 'deepseek', 'claude'])]
        valid_sequences = [opt for opt in sequence_options if '/' in opt and any('K' in opt for K in ['K', 'k'])]

        print(f"Valid models: {valid_models}")
        print(f"Valid sequences: {valid_sequences}")

        # 保存初始选项数据
        initial_data = {
            'timestamp': time.time(),
            'url': driver.current_url,
            'title': driver.title,
            'all_model_options': model_options,
            'all_sequence_options': sequence_options,
            'valid_models': valid_models,
            'valid_sequences': valid_sequences
        }

        with open('json_data/initial_options.json', 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)

        # 测试组合
        combinations = []

        for model in valid_models[:2]:  # 限制为前2个模型
            for sequence in valid_sequences[:2]:  # 限制为前2个序列
                print(f"\n=== Testing: {model} + {sequence} ===")

                # 清除之前的数据
                driver.execute_script("window.jsonResponses = [];")

                # 选择模型
                print(f"Selecting model: {model}")
                model_selected = select_option_by_text(driver, model)

                if model_selected:
                    time.sleep(2)

                    # 选择序列
                    print(f"Selecting sequence: {sequence}")
                    sequence_selected = select_option_by_text(driver, sequence)

                    if sequence_selected:
                        time.sleep(3)  # 等待数据加载

                        # 获取JSON数据
                        data_count = wait_for_json_data(driver)
                        json_data = driver.execute_script("return window.jsonResponses || [];")

                        print(f"Captured {data_count} JSON responses")

                        # 保存组合数据
                        combo_data = {
                            'combination': f"{model}_{sequence}",
                            'model': model,
                            'sequence': sequence,
                            'timestamp': time.time(),
                            'data_count': data_count,
                            'json_responses': json_data
                        }

                        combinations.append(combo_data)

                        # 如果有数据，保存单独的文件
                        if json_data:
                            filename = f"json_data/combo_{model.replace(' ', '_').replace('/', '_')}_and_{sequence.replace(' ', '_').replace('/', '_')}.json"
                            with open(filename, 'w', encoding='utf-8') as f:
                                json.dump(combo_data, f, indent=2, ensure_ascii=False)
                            print(f"Saved detailed data to: {filename}")

                time.sleep(1)  # 组合之间的间隔

        # 保存汇总结果
        final_result = {
            'timestamp': time.time(),
            'total_combinations_tested': len(combinations),
            'successful_combinations': len([c for c in combinations if c['json_responses']]),
            'combinations': combinations
        }

        with open('json_data/final_results.json', 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)

        print(f"\n=== Summary ===")
        print(f"Total combinations tested: {len(combinations)}")
        print(f"Successful combinations: {len([c for c in combinations if c['json_responses']])}")
        print(f"Results saved to json_data/final_results.json")

        return final_result

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()