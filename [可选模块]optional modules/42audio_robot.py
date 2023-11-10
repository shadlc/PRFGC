#!/usr/bin/python
#音乐机器人模块处理
# 本模块是用来调用ts3音乐机器人的[https://github.com/Splamy/TS3AudioBot]

import global_variable as gVar
from ifunction import import_json, save_json, warnf, module_enable, reply, get_user_name, get_group_name, send_group_forward_msg, send_private_forward_msg
from print_color import RESET, LPURPLE

import re
import json
import time
import requests
from urllib.parse import quote

module_name = "音乐机器人"

data_file = 'data/audio_robot.json'
config = import_json(data_file)

class audio_robot:
  def __init__(self,rev,auth):
    self.success = True
    self.rev = rev
    self.post_type = self.rev["post_type"] if "post_type" in self.rev else ""
    self.post_time = self.rev["time"] if "time" in self.rev else ""
    self.msg_type = self.rev["message_type"] if "message_type" in self.rev else ""
    self.notice_type = self.rev["notice_type"] if "notice_type" in self.rev else ""
    self.sub_type = self.rev["sub_type"] if "sub_type" in self.rev else ""
    self.msg_id = self.rev["message_id"] if "message_id" in self.rev else ""
    self.rev_msg = self.rev["message"] if "message" in self.rev else ""
    self.user_id = self.rev["user_id"] if "user_id" in self.rev else 0
    self.user_name = get_user_name(str(self.user_id)) if self.user_id else ""
    self.group_id = self.rev["group_id"] if "group_id" in self.rev else 0
    self.group_name = get_group_name(str(self.group_id)) if self.group_id else ""
    self.target_id = self.rev["target_id"] if "target_id" in self.rev else 0
    self.target_name = get_user_name(str(self.target_id)) if self.target_id else ""
    self.operator_id = self.rev["operator_id"] if "operator_id" in self.rev else 0
    self.operator_name = get_user_name(str(self.operator_id)) if self.operator_id else ""

    #检测开头#号触发
    if re.search(r"^ts\s+\S+", self.rev_msg):
      self.rev_msg = self.rev_msg[2:].strip()
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if re.search(r'^帮助$',self.rev_msg): self.help(auth)
      elif auth<=2 and re.search(r'^(当前)?播放',self.rev_msg): self.play()
      elif auth<=2 and re.search(r'^暂停$',self.rev_msg): self.pause()
      elif auth<=2 and re.search(r'^(开启|打开|启动|关闭|禁止|取消)*随机播放$',self.rev_msg): self.random()
      elif auth<=2 and re.search(r'^(关闭|禁止|取消|单曲|列表)?循环(播放)?$',self.rev_msg): self.repeat()
      elif auth<=2 and re.search(r'(上一曲|上一首|下一首|下一曲)',self.rev_msg): self.change()
      elif auth<=2 and re.search(r'^(设置|设定|)音量',self.rev_msg): self.volume()
      elif auth<=2 and re.search(r'^我的歌单',self.rev_msg): self.my_list()
      elif auth<=2 and re.search(r'^(查询|查看)歌单',self.rev_msg): self.show_list()
      elif auth<=2 and re.search(r'^(新增|新建|增加|设置|重置|清除|清空|删除)歌单',self.rev_msg): self.set_list()
      elif auth<=2 and re.search(r'^歌单(新增|增加)',self.rev_msg): self.add_list()
      else: self.success = False
    else: self.success = False

  def help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=2:
      msg += '\n调用本模块请使用“ts ”开头，无需@我'
      msg += '\nts 播放 (我的歌单|歌单名) | 播放音乐（默认播放默认歌单）'
      msg += '\nts 暂停 | 暂停播放音乐'
      msg += '\nts (上一曲|下一曲) | 更改播放歌曲'
      msg += '\nts (开启|关闭)随机播放 | 开启或关闭随机播放音乐'
      msg += '\nts (关闭|单曲|列表)循环 | 更改循环播放模式'
      msg += '\nts 音量 [百分比] | 更改机器人音量'
      msg += '\nts 我的歌单 [歌单名] | 设置我的歌单'
      msg += '\nts 查询歌单 (歌单名) | 获取全部歌单列表或特定歌单的歌曲详情'
      msg += '\nts (新增|设置|清空|删除)歌单 [歌单名] (歌曲文件夹) | 对歌单进行各种操作'
      msg += '\nts 歌单增加 [歌单名] [歌曲文件夹] | 为歌单增加新的歌曲'
    else:
      msg = '您无权限操作本模块~'
    reply(self.rev, msg)

  def play(self):
    new_connecting = False
    if query_status() != 2:
      new_connecting = True
      exe_cmd("disconnect")
      time.sleep(0.5)
      exe_cmd("connect")
      time.sleep(0.5)
    if re.search(r'^(当前)?播放$',self.rev_msg):
      if new_connecting:
        resp = exe_cmd("list_play", "default")
      else:
        resp = exe_cmd("play")
      info = resp.get("result")
      if resp.get("code") != 200 or resp.get("error"):
        msg = resp.get("error")
      elif info[1].get("Paused") == True:
        msg = f'已暂停播放！当前曲目：{info[1].get("Link", "未知")}'
      elif info[1].get("Paused") == False:
        msg = f'已播放！当前曲目：{info[1].get("Link", "未知")}'
    elif re.search(r'^播放\s*我的歌单$',self.rev_msg):
      list_name = config["play_list"].get(str(self.user_id))
      if list_name:
        resp = exe_cmd("list_play", list_name)
        if resp.get("code") == 204:
          msg = f'已播放歌单《{list_name}》！'
        else:
          msg = resp.get("error")
      else:
        msg = f'你还没有设置自己的歌单~'
    elif re.search(r'^播放\s*(\S+)$',self.rev_msg):
      list_name = re.search(r'^播放\s*(\S+)$',self.rev_msg).groups()[0]
      resp = exe_cmd("list_play", list_name)
      if resp.get("code") == 204:
        msg = f'已播放歌单《{list_name}》！'
      else:
        msg = resp.get("error")
        if "The playlist could not be found." in msg:
          resp = exe_cmd("get_play_list")
          info = resp.get("result")
          play_list = [i.get("Id") for i in info]
          msg = "未查询到该歌单~\n现存歌单列表：\n- " + ("\n- ").join(play_list)
    reply(self.rev, msg)

  def pause(self):
    if query_status() != 2:
      exe_cmd("connect")
      time.sleep(0.5)
    resp = exe_cmd("pause")
    info = resp.get("result")
    if resp.get("code") != 200:
      msg = resp.get("error")
    if info[1].get("Paused") == True:
      msg = f'已暂停播放音乐！'
    elif info[1].get("Paused") == False:
      msg = f'已播放音乐！'
    reply(self.rev, msg)

  def random(self):
    if re.search(r'^(禁止|取消|关闭)',self.rev_msg):
      resp = exe_cmd("random", "off")
    else:
      resp = exe_cmd("random", "on")
    info = resp.get("result")
    if resp.get("code") != 200:
      msg = resp.get("error")
    elif info[1]:
      msg = f'已开启随机播放！'
    elif not info[1]:
      msg = f'已关闭随机播放！'
    reply(self.rev, msg)

  def repeat(self):
    if re.search(r'^(禁止|取消|关闭)循环',self.rev_msg):
      resp = exe_cmd("repeat", "off")
    elif re.search(r'^单曲循环',self.rev_msg):
      resp = exe_cmd("repeat", "one")
    else:
      resp = exe_cmd("repeat", "all")
    info = resp.get("result")
    if resp.get("code") != 200:
      msg = resp.get("error")
    elif info[1] == 0:
      msg = f'已关闭循环播放！'
    elif info[1] == 1:
      msg = f'已设置为单曲循环播放！'
    elif info[1] == 2:
      msg = f'已设置为列表循环播放！'
    reply(self.rev, msg)

  def change(self):
    if re.search(r'(上一首|上一曲)',self.rev_msg):
      resp = exe_cmd("previous")
    elif re.search(r'(下一首|下一曲)',self.rev_msg):
      resp = exe_cmd("next")
    info = resp.get("result")
    if resp.get("code") != 200:
      msg = resp.get("error")
    else:
      song_name = info[1].get("Link").rsplit("/", 1)[1]
      msg = f'已切换~当前播放：{song_name}'
    reply(self.rev, msg)

  def volume(self):
    if re.search(r'(?:[1-9]\d?|100)',self.rev_msg):
      value = re.search(r'(?:[1-9]\d?|100)',self.rev_msg).group(0)
      resp = exe_cmd("volume", value)
      info = resp.get("result")
      if resp.get("code") != 200:
        msg = resp.get("error")
      else:
        msg = f"已调整音量为{int(info[1])}%"
    else:
      msg = "请输入0~100的整数作为音量百分比~"
    reply(self.rev, msg)

  def my_list(self):
    if re.search(r'^我的歌单\s*(\S+)',self.rev_msg):
      list_name = re.search(r'^我的歌单\s*(\S+)',self.rev_msg).groups()[0]
      latest_list_name = config["play_list"].get(str(self.user_id))
      config["play_list"][str(self.user_id)] = list_name
      save_json(data_file, config)
      if latest_list_name:
        msg = f"已将您的歌单从《{latest_list_name}》改为《{list_name}》"
      else:
        msg = f"已将您的歌单设置为《{list_name}》"
    else:
      play_list_name = config["play_list"].get(str(self.user_id))
      if play_list_name:
        msg = f"您的歌单目前为“{play_list_name}”\n发送“ts 查询歌单 我的歌单”获取歌单歌曲详情"
      else:
        msg = f"您的歌单不存在~请使用“ts 我的歌单 [歌单名]”绑定吧~"
    reply(self.rev, msg)

  def show_list(self):
    if re.search(r'^(查询|查看)歌单\s*(\S+)',self.rev_msg):
      play_list_name = re.search(r'^(查询|查看)歌单\s*(\S+)',self.rev_msg).group(2)
      if play_list_name == "我的歌单":
        play_list_name = config["play_list"].get(str(self.user_id))
        if play_list_name == None:
          msg = "您的歌单不存在~请使用“ts 我的歌单 [歌单名]”绑定吧~"
          reply(self.rev, msg)
          return
      resp = exe_cmd("show_play_list", play_list_name)
      info = resp.get("result")
      if resp.get("code") != 200 and resp.get("code") != 422:
        msg = resp.get("error")
      elif resp.get("code") == 422:
        msg = f"该歌单“{play_list_name}”不存在~"
      else:
        song_count = info.get("SongCount", "0")
        if song_count:
          msg_list = []
          content = f'歌单《{play_list_name}》共有{song_count}首音乐'
          msg_list.append({'type': 'node', 'data': {'name': gVar.self_name, 'uin': gVar.self_id, 'content': content}})
          for page in range(song_count // 20 + 1):
            resp = exe_cmd("show_play_list", play_list_name, f"{page*20}/20")
            info = resp.get("result")
            song_list = info.get("Items", [])
            for i in range(len(song_list)):
              content = f"{page*20+i+1}. " + song_list[i].get("Link")
              msg_list.append({'type': 'node', 'data': {'name': gVar.self_name, 'uin': gVar.self_id, 'content': content}})
          if self.group_id:
            send_group_forward_msg(self.group_id, msg_list)
          else:
            send_private_forward_msg(self.user_id, msg_list)
          return
        else:
          msg = f"歌单《{play_list_name}》为空！"

    else:
      resp = exe_cmd("get_play_list")
      info = resp.get("result")
      if resp.get("code") != 200:
        msg = resp.get("error")
      else:
        play_list = [i.get("Id") for i in info]
        msg = "全部歌单列表：\n- " + ("\n- ").join(play_list)
    reply(self.rev, msg)

  def set_list(self):
    if re.search(r'^(新增|新建|增加|设置|重置|清除|清空|删除)歌单\s+(\S+)',self.rev_msg):
      temp = re.search(r'^(新增|新建|增加|设置|重置|清除|清空|删除)歌单\s+(\S+)\s*(\S*)',self.rev_msg).groups()
      play_list_name = temp[1]
      music_dir = temp[2]
      if play_list_name == "我的歌单":
        play_list_name = config["play_list"].get(str(self.user_id))
        if play_list_name == None:
          msg = "您的歌单不存在~请使用“ts 我的歌单 [歌单名]”绑定吧~"
          reply(self.rev, msg)
          return

      resp = exe_cmd("show_play_list", play_list_name)
      info = resp.get("result")
      if resp.get("code") != 200 and resp.get("code") != 422:
        msg = resp.get("error")
        reply(self.rev, msg)
        return
      elif resp.get("code") == 422:
        if re.search(r'(重置|清除|清空|删除)',self.rev_msg):
          msg = "该歌单不存在"
          reply(self.rev, msg)
          return
        else:
          exe_cmd("create_play_list", play_list_name)
          time.sleep(0.5)
      else:
        if re.search(r'(重置|清除|清空)',self.rev_msg):
          resp = exe_cmd("clear_play_list", play_list_name)
          if resp.get("code") == 200:
            msg = f"重置歌单《{play_list_name}》成功！"
          else:
            msg = resp.get("error")
          reply(self.rev, msg)
          return
          
        elif re.search(r'删除',self.rev_msg):
          resp = exe_cmd("delete_play_list", play_list_name)
          if resp.get("code") == 204:
            msg = f"删除歌单《{play_list_name}》成功！"
          else:
            msg = resp.get("error")
          reply(self.rev, msg)
          return
        elif re.search(r'(设置|重置)',self.rev_msg):
          resp = exe_cmd("clear_play_list", play_list_name)
          if resp.get("code") == 200:
            pass
          else:
            msg = resp.get("error")
            reply(self.rev, msg)
            return
        else:
          msg = f"歌单《{play_list_name}》已存在！"
          reply(self.rev, msg)
          return

      if music_dir:
        resp = exe_cmd("import_play_list", play_list_name, music_dir)
        info = resp.get("result")
        if resp.get("code") != 200:
          msg = resp.get("error")
        else:
          msg = f'已为歌单《{play_list_name}》设置歌曲文件夹[{music_dir}]！\n当前歌曲数量为{info.get("SongCount","0")}首\n发送“ts 查询歌单 {play_list_name}”获取歌单歌曲详情'
      else:
        resp = exe_cmd("show_play_list", play_list_name)
        info = resp.get("result")
        if resp.get("code") != 200:
          msg = resp.get("error")
          reply(self.rev, msg)
        else:
          msg = f'创建歌单《{play_list_name}》成功！'
    else:
      msg = f'请输入歌单名与目录名，示例：\n新增歌单 default\n设置歌单 default /music/default\n重置歌单 default\n删除歌单 default'
    reply(self.rev, msg)

  def add_list(self):
    if re.search(r'^歌单(新增|增加)\s+(\S+)\s+(.+)',self.rev_msg):
      temp = re.search(r'^歌单(新增|增加)\s+(\S+)\s+(.+)',self.rev_msg).groups()
      play_list_name = temp[1]
      music_dir = temp[2]
      if play_list_name == "我的歌单":
        play_list_name = config["play_list"].get(str(self.user_id))
        if not play_list_name:
          msg = "你还没有设置“我的歌单”，请使用\n我的歌单 [歌单名]\n来设置你的歌单吧~"
          reply(self.rev, msg)
          return

      resp = exe_cmd("show_play_list", play_list_name)
      info = resp.get("result")
      if resp.get("code") != 200 and resp.get("code") != 422:
        msg = resp.get("error")
        reply(self.rev, msg)
        return
      elif resp.get("code") == 422:
        exe_cmd("create_play_list", play_list_name)
        time.sleep(0.5)
      else:
        pass

      if music_dir:
        resp = exe_cmd("import_play_list", play_list_name, music_dir)
        info = resp.get("result")
        if resp.get("code") != 200:
          msg = resp.get("error")
        else:
          msg = f'已为歌单《{play_list_name}》增加歌曲文件夹[{music_dir}]内的全部歌曲！\n当前歌曲数量为{info.get("SongCount","0")}首\n发送“ts 查询歌单 {play_list_name}”获取歌单歌曲详情'
      else:
        resp = exe_cmd("show_play_list", play_list_name)
        info = resp.get("result")
        if resp.get("code") != 200:
          msg = resp.get("error")
        else:
          msg = f"创建歌单《{play_list_name}》成功！"
    else:
      msg = f'请输入歌单名与目录名，示例：\n 设置歌单 default /music/default'
    reply(self.rev, msg)

def query_status():
  resp = exe_cmd("list")
  info = resp.get("result")
  if info and "ErrorName" in info:
    return 2
  elif info:
    return info[0].get("Status")
  return 0

def exe_cmd(cmd_type, data="", data_b=""):
  info = ""
  error = ""
  try:
    resp = audio_robot_get(cmd_type, data, data_b)
  except Exception as e:
    error = f"网络故障: {e}"
    return {"code": 0, "result": "", "error": error}
  if resp.text:
    try:
      info = json.loads(resp.text)
    except ValueError:
      info = ""
  else:
    info = ""
  if resp.status_code != 200 and "ErrorName" not in info:
    error = f'音乐机器人连接故障！返回值：{resp.status_code}'
  if info and "ErrorName" in info:
    error = f'调用失败！返回值：{resp.status_code}，原因：{info.get("ErrorName","")} {info.get("ErrorMessage","")} {info.get("HelpMessage","")}'
  return {"code": resp.status_code, "result": info, "error": error}

def audio_robot_get(cmd_type, data="", data_b=""):
  suffix_url = ""
  cmd_list = {
    "list": "/api/bot/list",
    "info": "/api/bot/use/0/(/server/tree)",
    "playing": "/api/bot/use/0/(/song)",
    "connect": "/api/bot/connect/template/bot",
    "disconnect": "/api/bot/use/0/(/bot/disconnect)",
    "pause": "/api/bot/use/0/(/json/merge/(/pause)/(/song))",
    "play": "/api/bot/use/0/(/json/merge/(/play)/(/song))",
    "repeat": f"/api/bot/use/0/(/json/merge/(/repeat/{quote(data)})/(/repeat))",
    "random": f"/api/bot/use/0/(/json/merge/(/random/{quote(data)})/(/random))",
    "previous": "/api/bot/use/0/(/json/merge/(/previous)(/song))",
    "next": "/api/bot/use/0/(/json/merge/(/next)(/song))",
    "volume": f"/api/bot/use/0/(/json/merge/(/volume/{quote(data, safe='')})/(/volume))",
    "list_play": f"/api/bot/use/0/(/list/play/{quote(data, safe='')})",
    "get_play_list": "/api/bot/use/0/(/list/list)",
    "show_play_list": f"/api/bot/use/0/(/list/show/{quote(data, safe='')}/{data_b})",
    "create_play_list": f"/api/bot/use/0/(/list/create/{quote(data, safe='')}/{quote(data, safe='')})",
    "import_play_list": f"/api/bot/use/0/(/list/import/{quote(data, safe='')}/{quote(data_b, safe='')})",
    "delete_play_list": f"/api/bot/use/0/(/list/delete/{quote(data, safe='')})",
    "clear_play_list": f"/api/bot/use/0/(/json/merge/(/list/clear/{quote(data, safe='')})/(/list/show/{quote(data, safe='')})",
  }
  if cmd_type in cmd_list:
    suffix_url = cmd_list[cmd_type]
  url = config["bot_url"] + suffix_url
  resp = requests.get(url, headers={"authorization": config["bot_authorization"]}, timeout=(5, 5))
  if gVar.is_debug:
    warnf(f"[{module_name}] 请求URL：{LPURPLE}{url}{RESET} 返回：{resp.text}")
  return resp





if config == {}:
  warnf(f"尚未对 [{module_name}] 模块进行配置,未加载！")
  config = {"bot_url": "", "bot_authorization": "", "play_list": {}}
  save_json(data_file, config)
else:
  module_enable(module_name, audio_robot)