#!/usr/bin/env python3
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def simple_test():
    # 尝试直接访问常见的API端点
    base_url = "https://inferencemax.semianalysis.com"
    possible_endpoints = [
        "/api/data",
        "/api/benchmarks",
        "/api/models",
        "/api/results",
        "/data.json",
        "/benchmarks.json",
        "/models.json"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': base_url
    }

    results = {}

    for endpoint in possible_endpoints:
        url = base_url + endpoint
        print(f"Testing: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    results[endpoint] = {
                        'status': response.status_code,
                        'data': data,
                        'content_type': response.headers.get('content-type')
                    }
                    print(f"✓ Success! Found JSON data at {endpoint}")
                except:
                    results[endpoint] = {
                        'status': response.status_code,
                        'text': response.text[:200],
                        'content_type': response.headers.get('content-type')
                    }
                    print(f"✓ Got response but not JSON at {endpoint}")
            else:
                print(f"✗ Status {response.status_code}")
                results[endpoint] = {
                    'status': response.status_code,
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            print(f"✗ Error: {e}")
            results[endpoint] = {
                'error': str(e)
            }

    # 保存结果
    with open('json_data/api_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to json_data/api_test_results.json")

    # 尝试用浏览器获取页面数据
    print("\nTrying to extract data from browser...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(base_url)
        time.sleep(5)

        # 执行JavaScript来查找数据
        script = """
        // 查找window对象上的数据
        var windowData = {};
        for (var key in window) {
            if (typeof window[key] === 'object' && window[key] !== null) {
                if (key.includes('data') || key.includes('config') || key.includes('model') || key.includes('benchmark')) {
                    try {
                        windowData[key] = JSON.parse(JSON.stringify(window[key]));
                    } catch (e) {
                        windowData[key] = 'Cannot serialize';
                    }
                }
            }
        }

        // 查找React props
        var reactData = [];
        var reactElements = document.querySelectorAll('[data-reactroot], [data-reactid]');
        reactElements.forEach(function(el) {
            if (el._reactInternalInstance || el.__reactInternalInstance) {
                reactData.push({
                    element: el.tagName,
                    hasReactData: true
                });
            }
        });

        // 查找script标签中的数据
        var scriptData = [];
        var scripts = document.querySelectorAll('script:not([src])');
        scripts.forEach(function(script) {
            var text = script.textContent;
            if (text.includes('data:') || text.includes('benchmark') || text.includes('performance')) {
                scriptData.push(text.substring(0, 1000));
            }
        });

        return {
            windowData: windowData,
            reactData: reactData,
            scriptData: scriptData,
            pageTitle: document.title,
            pageUrl: window.location.href
        };
        """

        page_data = driver.execute_script(script)

        # 保存页面数据
        with open('json_data/page_data.json', 'w', encoding='utf-8') as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)

        print(f"Page data saved to json_data/page_data.json")

        return results, page_data

    except Exception as e:
        print(f"Browser error: {e}")
        return results, None

    finally:
        driver.quit()

if __name__ == "__main__":
    simple_test()