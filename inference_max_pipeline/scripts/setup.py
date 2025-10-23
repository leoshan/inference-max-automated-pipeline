#!/usr/bin/env python3
"""
InferenceMAX 数据管道安装脚本
用于安装依赖、检查环境和设置系统服务
"""

import os
import sys
import subprocess
import yaml
import logging
from pathlib import Path

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('SetupScript')

def check_python_version():
    """检查Python版本"""
    logger = logging.getLogger('SetupScript')
    version = sys.version_info
    logger.info(f"Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 7):
        logger.error("需要Python 3.7或更高版本")
        return False

    return True

def install_dependencies():
    """安装Python依赖"""
    logger = logging.getLogger('SetupScript')
    logger.info("检查和安装Python依赖...")

    required_packages = [
        'pyyaml>=6.0',
        'selenium>=4.0',
        'schedule>=1.0',
        'requests>=2.25'
    ]

    for package in required_packages:
        try:
            __import__(package.split('>=')[0].replace('-', '_'))
            logger.info(f"✅ {package} 已安装")
        except ImportError:
            logger.info(f"📦 安装 {package}...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                             check=True, capture_output=True)
                logger.info(f"✅ {package} 安装成功")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ {package} 安装失败: {e}")
                return False

    return True

def check_chrome_driver():
    """检查ChromeDriver"""
    logger = logging.getLogger('SetupScript')
    logger.info("检查ChromeDriver安装...")

    try:
        result = subprocess.run(['chromedriver', '--version'],
                              capture_output=True, text=True)
        logger.info(f"✅ ChromeDriver已安装: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        logger.error("❌ ChromeDriver未找到")
        logger.info("请安装ChromeDriver:")
        logger.info("1. 下载: https://chromedriver.chromium.org/")
        logger.info("2. 解压到 /usr/local/bin/chromedriver")
        logger.info("3. 添加执行权限: chmod +x /usr/local/bin/chromedriver")
        return False

def create_directories():
    """创建必要的目录"""
    logger = logging.getLogger('SetupScript')

    directories = [
        'json_data/raw_json_files',
        'inference_max_pipeline/config',
        'inference_max_pipeline/logs',
        'inference_max_pipeline/data_archive',
        'inference_max_pipeline/reports',
        'inference_max_pipeline/scripts'
    ]

    base_dir = Path.cwd()
    for dir_path in directories:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ 创建目录: {full_path}")

    return True

def setup_permissions():
    """设置文件权限"""
    logger = logging.getLogger('SetupScript')

    scripts = [
        'inference_max_pipeline/scripts/inference_max_pipeline.py',
        'inference_max_pipeline/scripts/scheduler.py',
        'inference_max_pipeline/scripts/setup.py'
    ]

    base_dir = Path.cwd()
    for script in scripts:
        script_path = base_dir / script
        if script_path.exists():
            os.chmod(script_path, 0o755)
            logger.info(f"✅ 设置执行权限: {script_path}")

    return True

def create_systemd_service():
    """创建systemd服务文件"""
    logger = logging.getLogger('SetupScript')

    service_content = """[Unit]
Description=InferenceMAX Data Pipeline Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={}
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart={} --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
""".format(
    Path.cwd(),
    sys.executable + " " + str(Path.cwd() / "inference_max_pipeline/scripts/scheduler.py")
)

    service_file = Path("/etc/systemd/system/inference-max-pipeline.service")

    try:
        with open(service_file, 'w') as f:
            f.write(service_content)

        logger.info(f"✅ 创建systemd服务文件: {service_file}")
        logger.info("使用以下命令启用服务:")
        logger.info("  sudo systemctl daemon-reload")
        logger.info("  sudo systemctl enable inference-max-pipeline")
        logger.info("  sudo systemctl start inference-max-pipeline")

        return True
    except Exception as e:
        logger.error(f"❌ 创建systemd服务失败: {e}")
        return False

def create_crontab_entry():
    """创建crontab条目"""
    logger = logging.getLogger('SetupScript')

    cron_entry = f"# InferenceMAX Data Pipeline - 每天凌晨2点执行\n"
    cron_entry += f"0 2 * * * cd {Path.cwd()} && {sys.executable} {Path.cwd()}/inference_max_pipeline/scripts/scheduler.py --once >> {Path.cwd()}/inference_max_pipeline/logs/cron.log 2>&1\n"

    logger.info("Crontab条目:")
    logger.info(cron_entry)
    logger.info("使用以下命令添加到crontab:")
    logger.info("  crontab -e")
    logger.info("  然后将上述内容粘贴进去")

def test_pipeline():
    """测试管道"""
    logger = logging.getLogger('SetupScript')
    logger.info("测试数据管道...")

    try:
        result = subprocess.run([
            sys.executable,
            str(Path.cwd() / "inference_max_pipeline/scripts/scheduler.py"),
            "--once"
        ], capture_output=True, text=True, timeout=600)  # 10分钟超时

        if result.returncode == 0:
            logger.info("✅ 管道测试成功")
            return True
        else:
            logger.error(f"❌ 管道测试失败:")
            logger.error(f"标准输出: {result.stdout}")
            logger.error(f"错误输出: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("❌ 管道测试超时")
        return False
    except Exception as e:
        logger.error(f"❌ 管道测试异常: {e}")
        return False

def main():
    """主安装函数"""
    print("🚀 InferenceMAX 数据管道安装程序")
    print("="*50)

    logger = setup_logging()

    steps = [
        ("检查Python版本", check_python_version),
        ("安装Python依赖", install_dependencies),
        ("检查ChromeDriver", check_chrome_driver),
        ("创建目录结构", create_directories),
        ("设置文件权限", setup_permissions),
    ]

    failed_steps = []

    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            failed_steps.append(step_name)
            print(f"❌ {step_name} 失败")
        else:
            print(f"✅ {step_name} 完成")

    if failed_steps:
        print(f"\n❌ 安装失败，以下步骤需要手动处理:")
        for step in failed_steps:
            print(f"  - {step}")
        return False

    print(f"\n🎉 基础安装完成！")
    print(f"\n📋 后续配置选项:")

    print(f"\n1️⃣ 创建系统服务 (推荐):")
    if create_systemd_service():
        print("   systemd服务文件已创建")
    else:
        print("   请手动创建系统服务")

    print(f"\n2️⃣ 设置定时任务:")
    create_crontab_entry()

    print(f"\n3️⃣ 测试管道:")
    print("   python inference_max_pipeline/scripts/scheduler.py --once")

    test_choice = input("\n是否现在测试管道? (y/n): ").lower().strip()
    if test_choice == 'y':
        print("\n🧪 开始测试管道...")
        if test_pipeline():
            print("✅ 管道测试成功!")
        else:
            print("❌ 管道测试失败，请检查日志")
            return False

    print(f"\n📖 使用说明:")
    print(f"   - 执行一次: python inference_max_pipeline/scripts/scheduler.py --once")
    print(f"   - 守护进程: python inference_max_pipeline/scripts/scheduler.py --daemon")
    print(f"   - 测试调度: python inference_max_pipeline/scripts/scheduler.py --test")

    print(f"\n📁 重要目录:")
    print(f"   - 配置: inference_max_pipeline/config/")
    print(f"   - 日志: inference_max_pipeline/logs/")
    print(f"   - 数据归档: inference_max_pipeline/data_archive/")
    print(f"   - 报告: inference_max_pipeline/reports/")

    print(f"\n🎊 安装完成！数据管道已准备就绪。")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n安装过程中发生异常: {e}")
        sys.exit(1)