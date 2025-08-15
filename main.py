#!/usr/bin/python
# 机器人启动入口，由外部方法调用最佳

import threading
import platform
import random
import signal
import time
import sys

from colorama import Fore

from src.api import connect_api
from src.robot import Concerto

robot = Concerto()

# 检测运行平台是否为Linux，导入readline模块实现TAB补全和历史命令读取
if platform.system() == "Linux":
    import readline

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

# 启动主函数
if __name__ == "__main__":
    robot.printf(random.choice([Fore.BLACK,Fore.RED,Fore.GREEN,Fore.YELLOW,Fore.BLUE,Fore.MAGENTA,Fore.CYAN,Fore.WHITE]) + robot.start_info + Fore.RESET, flush=True)
    robot.printf("ConcertoBot启动中，正在连接API...", end="", console=False)
    connect_api(robot)
    robot.printf(f"已接入账号: {Fore.MAGENTA}{robot.self_name}({robot.self_id}){Fore.RESET}")
    robot.import_modules()
    threading.Thread(target=robot.listening_msg, daemon=True).start()
    threading.Thread(target=robot.listening_console, daemon=True).start()

    while robot.is_running:
        time.sleep(0.1)
    if robot.is_restart:
        sys.exit(1)
    else:
        sys.exit(0)
