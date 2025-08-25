"""机器人启动入口"""

import os
import threading
import platform
import logging
import random
import signal
import time
import sys

from logging.handlers import TimedRotatingFileHandler
from colorama import Fore

from src.api import connect_api
from src.robot import Concerto

robot = Concerto()

# 检测运行平台是否为Linux，导入readline模块实现TAB补全和历史命令读取
if platform.system() == "Linux":
    import readline # pylint: disable=import-error

    # 命令自动补全
    def completer(text, state):
        options = [cmd for cmd in robot.cmd if cmd.startswith(text)]
        if state < len(options):
            return options[state]
        else:
            return None

    readline.parse_and_bind("tab: complete")
    readline.set_completer(completer)

# 读取Ctrl C信号
def my_handler(signum, frame):
    robot.warnf("正在关闭程序...")
    robot.is_running = False
    sys.exit()

signal.signal(signal.SIGINT, my_handler)

# 日志记录
logger = logging.getLogger()
logger.setLevel(logging.INFO)

os.makedirs(robot.config.log_path, exist_ok=True)
handler = TimedRotatingFileHandler(
    os.path.join(robot.config.log_path, "bot.log"),
    when="midnight",
    interval=1,
    encoding="utf-8"
)
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# 启动主函数
if __name__ == "__main__":
    robot.printf(random.choice([Fore.BLACK,Fore.RED,Fore.GREEN,Fore.YELLOW,Fore.BLUE,Fore.MAGENTA,Fore.CYAN,Fore.WHITE]) + robot.start_info + Fore.RESET, flush=True)
    robot.printf(f"正在连接[{robot.config.api_base}]API...", end="", console=False)
    connect_api(robot)
    robot.printf(f"已接入账号: {Fore.MAGENTA}{robot.self_name}({robot.self_id}){Fore.RESET}")
    robot.import_modules()
    threading.Thread(target=robot.listening_msg, daemon=True).start()
    threading.Thread(target=robot.listening_console, daemon=True).start()

    while robot.is_running:
        time.sleep(0.1)
    sys.exit(robot.is_restart)
