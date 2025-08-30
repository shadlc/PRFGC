#!/usr/bin/python
# 机器人启动入口，由外部方法调用最佳

import os
import threading
import platform
import logging
import signal
import time
import sys

from logging.handlers import TimedRotatingFileHandler

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
    robot.run()
    threading.Thread(target=robot.listening_msg, daemon=True, name="消息监听").start()
    threading.Thread(target=robot.listening_console, daemon=True, name="键盘监听").start()
    while robot.is_running:
        time.sleep(0.1)
    sys.exit(robot.is_restart)
