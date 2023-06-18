#!/usr/bin/python
#饥荒服务器操作模块

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

import re
import time
from subprocess import Popen, PIPE, run

module_name = '饥荒服务器操作模块'
tmux_name = ''

class dont_starve:
  def __init__(self,rev,auth):
    self.executing = False
    self.success = True
    self.rev = rev
    self.post_type = self.rev['post_type'] if 'post_type' in self.rev else ''
    self.post_time = self.rev['time'] if 'time' in self.rev else ''
    self.msg_type = self.rev['message_type'] if 'message_type' in self.rev else ''
    self.notice_type = self.rev['notice_type'] if 'notice_type' in self.rev else ''
    self.sub_type = self.rev['sub_type'] if 'sub_type' in self.rev else ''
    self.msg_id = self.rev['message_id'] if 'message_id' in self.rev else ''
    self.rev_msg = self.rev['message'] if 'message' in self.rev else ''
    self.user_id = self.rev['user_id'] if 'user_id' in self.rev else 0
    self.user_name = get_user_name(str(self.user_id)) if self.user_id else ''
    self.group_id = self.rev['group_id'] if 'group_id' in self.rev else 0
    self.group_name = get_group_name(str(self.group_id)) if self.group_id else ''
    self.target_id = self.rev['target_id'] if 'target_id' in self.rev else 0
    self.target_name = get_user_name(str(self.target_id)) if self.target_id else ''
    self.operator_id = self.rev['operator_id'] if 'operator_id' in self.rev else 0
    self.operator_name = get_user_name(str(self.operator_id)) if self.operator_id else ''

    #检测开头#号触发
    if re.search(r"^#\S+", self.rev_msg):
      self.rev_msg = self.rev_msg[1:]
      if auth<=2 and re.search(r'^帮助$', self.rev_msg): self.help(auth)
      elif auth<=2 and re.search(r'^运行状况$', self.rev_msg): self.status()
      elif auth<=1 and re.search(r'^重启(地上|洞穴)?(服务器)?$', self.rev_msg): self.restart()
      elif auth<=1 and re.search(r'^更新$', self.rev_msg): self.update()
      elif re.search(r'(在线玩家|玩家列表|公告|保存|停止|回档)', self.rev_msg) and detect_running() == 2: self.not_avaliable()
      elif auth<=2 and re.search(r'^(在线玩家|玩家列表)$', self.rev_msg): self.player_list()
      elif auth<=2 and re.search(r'^公告(.+)?$', self.rev_msg): self.announce()
      elif auth<=2 and re.search(r'^保存$', self.rev_msg): self.save()
      elif auth<=1 and re.search(r'^停止$', self.rev_msg): self.stop()
      elif auth<=1 and re.search(r'^回档$', self.rev_msg): self.rollback()
      else: self.success = False
    else: self.success = False

  def help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=1:
      msg += '\n#运行状况 | 查看服务器运行状况'
      msg += '\n#在线玩家 | 查看在线玩家'
      msg += '\n#公告 [文本] | 向服务器发送公告'
      msg += '\n#保存 | 服务器保存存档'
      msg += '\n#停止 | 停止服务器'
      msg += '\n#重启 | 重启或启动服务器'
      msg += '\n#更新 | 手动更新服务器'
      msg += '\n#回档 | 将服务器回档'
    if auth<=2:
      msg += '\n#运行状况 | 查看服务器运行状况'
      msg += '\n#在线玩家 | 查看在线玩家'
      msg += '\n#公告 [文本] | 向服务器发送公告'
      msg += '\n#保存 | 服务器保存存档'
    reply(self.rev,msg)

  def status(self):
    if detect_running() == 0:
      msg = '服务器正在运行中！'
      reply(self.rev,msg)
    elif detect_running() == 1:
      msg = '服务器已停止！请通过发送“#重启”启动服务器！'
      reply(self.rev,msg)
    elif detect_running() == 2:
      self.not_avaliable()
    

  def not_avaliable(self):
    msg = '服务器不可用！如需游玩，请通知管理员开服！'
    reply(self.rev,msg)

  def announce(self):
    if re.search(r'^公告\s?(.+)$', self.rev_msg):
      text = re.search(r'^公告\s?(.+)$', self.rev_msg).groups()[0]
      text = text.replace('"','\\\\\\\"')
      tmux_captured = send_command(f'c_announce(\\"{text}\\")\;')
      if 'RemoteCommandInput: "c_announce(' in tmux_captured:
        msg = '服务器公告已发送！'
      else:
        msg = '服务器公告发送失败！'
    else:
      msg = '请输入要发送的内容'
    reply(self.rev,msg)


  def player_list(self):
    tmux_captured = send_command('c_listallplayers()\;')
    players = tmux_captured.split('RemoteCommandInput: "c_listallplayers();"')[-1]
    count = 0
    msg = '服务器当前玩家列表：'
    for player in players.split(': '):
      player = player.replace('\n','')
      if re.search(r'\((.*)\) (.*) \<(.*)\>', player):
        pid, name, character = re.search(r'\((.*)\) (.*) \<(.*)\>', player).groups()
        count += 1
        msg += f'\n[{count}] {name}(游戏ID:{pid})正在使用角色<{character}>游玩'
    if count == 0:
      msg = '服务器当前无在线玩家'
    reply(self.rev,msg)

  def save(self):
    tmux_captured = send_command('c_save()\;')
    if 'RemoteCommandInput: "c_save();"' in tmux_captured:
      msg = '服务器保存指令已发送！'
    else:
      msg = '服务器保存失败！'
    reply(self.rev,msg)

  def stop(self):
    if self.executing:
      msg = '请等待当前上一完成！'
      reply(self.rev,msg)

    self.executing = True
    tmux_captured_master = send_command('c_shutdown()\;', f'{tmux_name}:0.0')
    tmux_captured_cave = send_command('c_shutdown()\;', f'{tmux_name}:0.1')
    if 'RemoteCommandInput: "c_shutdown();"' in tmux_captured_master and 'RemoteCommandInput: "c_shutdown();"' in tmux_captured_cave:
      msg = '服务器停止成功！'
    elif 'RemoteCommandInput: "c_shutdown();"' not in tmux_captured_master:
      msg = '洞穴服务器停止成功，地上服务器停止失败！'
    elif 'RemoteCommandInput: "c_shutdown();"' not in tmux_captured_cave:
      msg = '地上服务器停止成功，洞穴服务器停止失败！'
    else:
      msg = '服务器停止失败！'
    reply(self.rev,msg)
    self.executing = False

  def restart(self):
    if self.executing:
      msg = '请等待当前上一完成！'
      reply(self.rev,msg)
    self.executing = True
    tmux = run(f'tmux ls |grep {tmux_name}',shell=True,capture_output=True,encoding='utf-8').stdout
    if not tmux:
      msg = '服务器已彻底关闭，请联系管理员进行首次开启'
      reply(self.rev,msg)
      return

    tmux_captured_master = send_command('c_shutdown()\;', f'{tmux_name}:0.0')
    tmux_captured_cave = send_command('c_shutdown()\;', f'{tmux_name}:0.1')

    if tmux_captured_master or tmux_captured_cave:
      msg = '服务器正在重启中，请稍后...'
      reply(self.rev,msg)
    else:
      msg = '服务器正在启动中，请稍后...'
      reply(self.rev,msg)

    if not (detect_exited(f'{tmux_name}:0.0') and detect_exited(f'{tmux_name}:0.1')):
      msg = '服务器关闭失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return

    tmux_captured = send_command('./master.sh', f'{tmux_name}:0.0')
    if not detect_started(f'{tmux_name}:0.0'):
      msg = '地上服务器启动失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return
    msg = '地上服务器已开启！'
    reply(self.rev,msg)
    tmux_captured = send_command('./caves.sh', f'{tmux_name}:0.1')
    if not detect_started(f'{tmux_name}:0.1'):
      msg = '洞穴服务器启动失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return
    msg = '洞穴服务器已开启！'
    reply(self.rev,msg)
    self.executing = False

  def update(self):
    if self.executing:
      msg = '请等待当前上一完成！'
      reply(self.rev,msg)
    self.executing = True
    tmux = run(f'tmux ls |grep {tmux_name}',shell=True,capture_output=True,encoding='utf-8').stdout
    if not tmux:
      msg = '服务器已彻底关闭，请联系管理员进行首次开启'
      reply(self.rev,msg)
      return

    if detect_running() == 0:
      msg = '服务器正在运行中，为了更新，正在关闭服务器...'
      reply(self.rev,msg)
      tmux_captured_master = send_command('c_shutdown()\;', f'{tmux_name}:0.0')
      tmux_captured_cave = send_command('c_shutdown()\;', f'{tmux_name}:0.1')

      if not (detect_exited(f'{tmux_name}:0.0') and detect_exited(f'{tmux_name}:0.1')):
        msg = '服务器关闭失败！请联系管理员查看问题！'
        reply(self.rev,msg)
        return

    tmux_captured = send_command('../update.sh', f'{tmux_name}:0.0')
    if 'updating' not in tmux_captured:
      msg = '服务器更新脚本执行失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return
    msg = '服务器正在更新，这可能需要花费几分钟，请耐心等待！'
    reply(self.rev,msg)
    if not (detect_exited(f'{tmux_name}:0.0'), 600):
      msg = '服务器更新超时！请联系管理员查看问题！'
      reply(self.rev,msg)
      return

    msg = '服务器更新成功！正在启动中...'
    reply(self.rev,msg)

    tmux_captured = send_command('./master.sh', f'{tmux_name}:0.0')
    if not detect_started(f'{tmux_name}:0.0'):
      msg = '地上服务器启动失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return
    msg = '地上服务器已开启！'
    reply(self.rev,msg)
    tmux_captured = send_command('./caves.sh', f'{tmux_name}:0.1')
    if not detect_started(f'{tmux_name}:0.1'):
      msg = '洞穴服务器启动失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return
    msg = '洞穴服务器已开启！'
    reply(self.rev,msg)
    self.executing = False

  def rollback(self):
    if self.executing:
      msg = '请等待当前上一完成！'
      reply(self.rev,msg)
    self.executing = True
    tmux_captured = send_command('c_rollback()\;')
    if 'RemoteCommandInput: "c_rollback();"' in tmux_captured:
      msg = '服务器回档指令已发送！请稍后...'
    else:
      msg = '服务器回档失败！'
    reply(self.rev,msg)

    time.sleep(1)
    msg = '地上服务器回档中...'
    reply(self.rev,msg)
    if not detect_started(f'{tmux_name}:0.0'):
      msg = '地上服务器回档失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return
    msg = '地上服务器回档成功！'
    reply(self.rev,msg)

    time.sleep(1)

    msg = '洞穴服务器回档中...'
    reply(self.rev,msg)
    time.sleep(1)
    if not detect_started(f'{tmux_name}:0.1'):
      msg = '洞穴服务器回档失败！请联系管理员查看问题！'
      reply(self.rev,msg)
      return
    msg = '洞穴服务器回档成功！'
    reply(self.rev,msg)
    self.executing = False

def send_command(cmd, tid=tmux_name):
  printf(f'执行指令[{LYELLOW}tmux send-keys -t {tid} "{cmd}" Enter;sleep 0.1;tmux capture-pane -pt {tid}{RESET}]')
  tmux_captured = run(f'tmux send-keys -t {tid} "{cmd}" Enter;sleep 0.1;tmux capture-pane -pt {tid}',shell=True,capture_output=True,encoding='utf-8').stdout
  return tmux_captured

def detect_running():
  tmux_captured = run(f'tmux ls |grep {tmux_name}',shell=True,capture_output=True,encoding='utf-8').stdout
  if tmux_captured:
    tmux_captured = send_command('c_listallplayers()\;')
    if 'RemoteCommandInput: "c_listallplayers();"' in tmux_captured:
      return 0
    else:
      return 1
  else:
    return 2

def detect_exited(tid, max_time=60):
  start_time = time.time()
  while(time.time() - start_time <= max_time):
    tmux_captured = send_command('echo exited', tid)
    if 'exited' in tmux_captured.split('echo exited')[-1]:
      return True
    time.sleep(3)
  return False

def detect_started(tid, max_time=60):
  start_time = time.time()
  while(time.time() - start_time <= max_time):
    tmux_captured = send_command('c_listallplayers()\;', tid)
    if 'RemoteCommandInput: "c_listallplayers();"' in tmux_captured:
      return True
    time.sleep(3)
  return False




if tmux_name == '':
  warnf(f'[{module_name}] 模块已禁用，如需启用请先前先在一个tmux打开两个panel,然后启动一次饥荒服务器之后，将tmux_name填入正确值后使用')
else:
  module_enable(module_name, dont_starve)