#!/usr/bin/python
#作为全局变量使用

from collections import deque
from print_color import *

global cqhttp_url,get_port,listening_port,self_name,self_id,admin_id,rev_group,at_info
global is_running,is_restart,is_debug,is_slience,is_show_heartbeat,is_show_all_msg,is_show_image,is_image_color
global functions,data,latest_data,latest_send,min_image_width,max_image_width

is_running = True
is_restart = True

is_show_image = True
is_image_color = True

functions = []
admin_id = []
rev_group = []
latest_data = ''
latest_request = ''
self_message = deque()

class cache:
  user_name = dict()
  group_name = dict()

data = dict()
class memory(object):
  def __init__(self):
    self.past_message = deque(maxlen=10)
    self.past_notice = deque(maxlen=10)


config_file = 'config.ini'
QA_file = 'QA_data.txt'
start_info = '''
  ██████╗  ██████╗        ██████╗ ██████╗ ██╗  ██╗████████╗████████╗██████╗ 
 ██╔════╝ ██╔═══██╗      ██╔════╝██╔═══██╗██║  ██║╚══██╔══╝╚══██╔══╝██╔══██╗
 ██║  ███╗██║   ██║█████╗██║     ██║   ██║███████║   ██║      ██║   ██████╔╝
 ██║   ██║██║   ██║╚════╝██║     ██║▄▄ ██║██╔══██║   ██║      ██║   ██╔═══╝ 
 ╚██████╔╝╚██████╔╝      ╚██████╗╚██████╔╝██║  ██║   ██║      ██║   ██║     
  ╚═════╝  ╚═════╝        ╚═════╝ ╚══▀▀═╝ ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝     
'''
first_start_info = f'''
==================================================
欢迎使用GO-CQHTTP的Python处理程序，请进行初次设置
使用 {LCYAN}group main 群号{RESET} 设置主对接群
使用 {LCYAN}op 用户QQ{RESET} 设置管理员
使用 {LCYAN}info{RESET} 查看程序运行状态和核心信息
某些设置可以打开{LPURPLE}config.ini{RESET}进行修改
==================================================
'''