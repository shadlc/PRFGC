#!/usr/bin/python
#外部请求模块处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

import socket
import threading

module_name = "外部请求模块"

class webhook:
  def __init__(self,rev=None,auth=None):
    self.success = False

  def init(self, host, port):
    self.success = False
    self.host = host
    self.port = int(port)
    self.data = ''
    self.hook_hisotry = {}
    self.latest_type = ''
    self.latest_times = 0
    threading.Thread(target=self.start_server, daemon=True).start()

  def start_server(self):
    while True:
      self.handle_msg(self.receive_msg())
      time.sleep(0.01)

  def receive_msg(self):
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((self.host, self.port))
    server.listen(100)
    header = 'HTTP/1.1 200 OK\r\n\r\n'
    client, address = server.accept()
    respond = bytes()
    while True:
       data = client.recv(1024)
       respond += data
       if len(data) < 1024 or data[-1] == 10:
         break
    client.sendall(header.encode(encoding='utf-8'))
    rev_json = request_to_json(respond.decode(encoding='utf-8'))
    server.close()
    return rev_json

  def handle_msg(self, data):
    if data:
      self.data = data
      if self.latest_type != data.get('type'):
        self.latest_times = 0
      self.latest_type = data.get('type')

      printf(f"[{module_name}] 接收到一条类型为{data.get('type')}的外部请求")
      if gVar.is_debug:
        warnf(f"[{module_name}] {data}")
      if data.get('type') == "STREAM_STARTED":
        if self.no_repeat(1) and self.not_execute_before(20):
          execute.stream_start(data)
      elif data.get('type') == "STREAM_STOPPED":
        if self.no_repeat(1):
          self.execute_if_not_in(execute.stream_end, data, 'STREAM_STARTED', 20)

  def not_execute_before(self, second):
    hook_type = self.data.get('type')
    if hook_type in self.hook_hisotry:
      timestamp = self.hook_hisotry.get(hook_type)
      if int(time.time()) - timestamp < second:
        need_second = second - (int(time.time()) - timestamp)
        warnf(f"[{module_name}] 因离重复通知{hook_type}仍需{need_second}秒而取消通知")
        return False
    self.hook_hisotry[self.latest_type] = int(time.time())
    return True

  def no_repeat(self, times):
    hook_type = self.data.get('type')
    if hook_type == self.latest_type:
      self.latest_times += 1
      if self.latest_times > times:
        warnf(f"[{module_name}] 因重复执行{hook_type}次数达到{self.latest_times}而取消对通知")
        return False
    return True

  def execute_if_not_in(self, func, argv, hook_type, second):
    def detect_hook_type():
      count_second = 0
      while count_second <= second:
        if self.latest_type == hook_type:
          warnf(f"[{module_name}] 因在{second}秒内{hook_type}的发生而无法执行{argv.get('type')}的通知")
          return
        count_second += 1
        time.sleep(1)
      func(argv)

    threading.Thread(target=detect_hook_type, daemon=True).start()

class execute:
  def stream_start(data):
    name = data.get('eventData').get('name')
    title = data.get('eventData').get('streamTitle')
    summary = data.get('eventData').get('summary')
    # send_msg({
    #   'msg_type':'group',
    #   'number':'123456',
    #   'msg':f'{name}开播啦！\n{title} - {summary}'
    # })

  def stream_end(data):
    name = data.get('eventData').get('name')
    # send_msg({
    #   'msg_type':'group',
    #   'number':'123456',
    #   'msg':f'{name}已经结束直播啦！'
    # })

server = webhook()
server.init('192.168.163.1','5702')
module_enable(module_name, webhook)