#!/usr/bin/python
#机器人启动入口，由外部方法调用最佳

import threading
import platform
import random
import curses
import signal
import json
import time
import sys
import re

from print_color import *
from ifunction import *

print(random.choice(ALL_COLOR) + gVar.start_info + RESET)

from handle import handle_msg,handle_console
from api_cqhttp import *
import global_variable  as gVar

#检测运行平台是否为Linux，导入readline模块实现TAB补全和历史命令读取
sysytem_platform = platform.system()
if sysytem_platform == 'Linux':
	import readline
	#命令自动补全
	def completer(text, state):
	    options = [cmd for cmd in gVar.CMD.keys() if cmd.startswith(text)]
	    if state < len(options):
	        return options[state]
	    else:
	        return None
	readline.parse_and_bind("tab: complete")
	readline.set_completer(completer)

	#读取Ctrl C信号
	def my_handler(signum, frame):
		warnf(f'正在关闭程序...')
		gVar.is_running = False
		sys.exit()
	signal.signal(signal.SIGINT, my_handler)

#监听来自cqhttp的请求
def listening_msg():
	while gVar.is_running:
		handle_msg(receive_msg())

#监听来自终端的输入并处理
def listening_console():
	while gVar.is_running:
		handle_console(input(f'\r{LGREEN}<console>{RESET} '))

#初始化机器人并进行信息和终端监听
def init():
	init_config()
	printf('CQHttp机器人已启动，正在连接CQHttp...', end='', console=False)
	connect_cqhttp()
	printf(f'正在监听来自{LPURPLE}{gVar.self_name}({gVar.self_id}){RESET}的消息')

	message_thread = threading.Thread(target=listening_msg)
	message_thread.setDaemon(True)
	message_thread.start()
	console_thread = threading.Thread(target=listening_console)
	console_thread.setDaemon(True)
	console_thread.start()

#启动主函数
if __name__ == '__main__':
	init()
	while gVar.is_running:pass
	if gVar.is_restart:
		sys.exit(1)
	else:
		sys.exit(0)
