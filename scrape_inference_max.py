#!/usr/bin/env python3
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_json_from_network(driver):
    """从网络请求中提取JSON数据"""
    # 获取网络日志
    logs = driver.get_log('performance')
    json_data = []

    for log in logs:
        message = json.loads(log['message'])
        if message['message']['method'] == 'Network.responseReceived':
            response = message['message']['params']['response']
            if 'json' in response.get('mimeType', '').lower():
                url = response['url']
                print(f"Found JSON response from: {url}")
                try:
                    # 尝试获取响应内容
                    request_id = message['message']['params']['requestId']
                    # 这里需要额外的处理来获取响应体
                except Exception as e:
                    print(f"Error extracting JSON: {e}")

    return json_data

def find_dropdowns(driver):
    """查找页面上的下拉框"""
    model_dropdowns = []
    isl_osl_dropdowns = []

    # 查找所有按钮
    buttons = driver.find_elements(By.TAG_NAME, 'button')

    for button in buttons:
        text = button.text.strip()
        if 'model' in text.lower() or any(x in text.lower() for x in ['gpt', 'llama', 'claude']):
            model_dropdowns.append(button)
        elif 'K' in text and '/' in text:  # 如 "1K / 1K"
            isl_osl_dropdowns.append(button)

    return model_dropdowns, isl_osl_dropdowns

def get_dropdown_options(driver, button):
    """获取下拉框的所有选项"""
    options = []
    try:
        # 点击按钮打开下拉框
        button.click()
        time.sleep(1)

        # 等待选项出现
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'li, [role="option"]'))
        )

        # 获取所有选项
        option_elements = driver.find_elements(By.CSS_SELECTOR, 'li, [role="option"]')
        options = [opt.text.strip() for opt in option_elements if opt.text.strip()]

        # 点击外部关闭下拉框
        driver.find_element(By.TAG_NAME, 'body').click()
        time.sleep(0.5)

    except Exception as e:
        print(f"Error getting dropdown options: {e}")

    return options

def capture_page_data(driver):
    """捕获页面中的数据"""
    try:
        # 执行JavaScript来获取页面数据
        data = driver.execute_script("""
            // 查找页面中的数据对象
            var pageData = {};

            // 查找React组件中的数据
            var reactElements = document.querySelectorAll('[data-reactroot], [data-reactid]');

            // 查找可能的配置数据
            var scripts = document.querySelectorAll('script');
            scripts.forEach(function(script) {
                var text = script.textContent;
                if (text.includes('data') || text.includes('config')) {
                    pageData.scripts = pageData.scripts || [];
                    pageData.scripts.push(text.substring(0, 500));
                }
            });

            return pageData;
        """)

        return data
    except Exception as e:
        print(f"Error capturing page data: {e}")
        return {}

def main():
    driver = setup_driver()

    try:
        print("Loading page...")
        driver.get("https://inferencemax.semianalysis.com/")
        time.sleep(5)

        # 启用网络日志
        driver.execute_cdp_cmd('Performance.enable', {})

        print("Finding dropdowns...")
        model_dropdowns, isl_osl_dropdowns = find_dropdowns(driver)

        print(f"Found {len(model_dropdowns)} model dropdowns")
        print(f"Found {len(isl_osl_dropdowns)} ISL/OSL dropdowns")

        all_data = {}

        # 测试模型下拉框
        for i, dropdown in enumerate(model_dropdowns):
            print(f"Getting options for model dropdown {i}")
            options = get_dropdown_options(driver, dropdown)
            print(f"Model options: {options[:5]}...")  # 只显示前5个

            all_data[f'model_dropdown_{i}'] = {
                'button_text': dropdown.text.strip(),
                'options': options
            }

        # 测试ISL/OSL下拉框
        for i, dropdown in enumerate(isl_osl_dropdowns):
            print(f"Getting options for ISL/OSL dropdown {i}")
            options = get_dropdown_options(driver, dropdown)
            print(f"ISL/OSL options: {options[:5]}...")

            all_data[f'isl_osl_dropdown_{i}'] = {
                'button_text': dropdown.text.strip(),
                'options': options
            }

        # 尝试不同的组合
        combinations = []
        if model_dropdowns and isl_osl_dropdowns:
            model_options = get_dropdown_options(driver, model_dropdowns[0])
            isl_osl_options = get_dropdown_options(driver, isl_osl_dropdowns[0])

            # 过滤有效选项
            model_options = [opt for opt in model_options if opt and 'Reset' not in opt]
            isl_osl_options = [opt for opt in isl_osl_options if opt and 'Reset' not in opt]

            # 创建一些测试组合
            for i in range(min(3, len(model_options))):
                for j in range(min(3, len(isl_osl_options))):
                    combo = {
                        'model': model_options[i],
                        'isl_osl': isl_osl_options[j],
                        'combination_id': f"{model_options[i]}_{isl_osl_options[j]}"
                    }
                    combinations.append(combo)

        # 捕获页面数据
        page_data = capture_page_data(driver)

        # 保存所有数据
        result = {
            'timestamp': time.time(),
            'url': driver.current_url,
            'title': driver.title,
            'dropdowns': all_data,
            'combinations': combinations,
            'page_data': page_data
        }

        # 保存到文件
        with open('json_data/inference_max_data.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Data saved to json_data/inference_max_data.json")
        print(f"Found {len(combinations)} combinations to test")

        return result

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()