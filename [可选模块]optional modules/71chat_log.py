#!/usr/bin/python
#消息处理模块

import os
import sys
import time
import jieba
import datetime
import traceback
import threading
import stylecloud

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

module_name = '消息处理模块'

stopwords_file = 'data/stopwords.txt'
font_file = 'data/AlibabaPuHuiTi95.ttf'
data_file = 'data/chat_log.json'
chat_log_dir = 'data/chat_log/'
if not os.path.exists(chat_log_dir):
  os.mkdir(chat_log_dir)
config = import_json(data_file)

class chat_log:
  def __init__(self,rev,auth):
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

    #初始化此模块需要的数据
    if self.group_id:
      self.owner_id = f'g{self.group_id}'
    else:
      self.owner_id = f'u{self.user_id}'
    if self.owner_id not in config:
      config[self.owner_id] = {'wordcloud': {'enable': False, 'icon': 'fas fa-square', 'palette': 'cartocolors.qualitative.Pastel_10'}}
    self.config = config[self.owner_id]

    try:
      self.user_record()
      if self.config['wordcloud']['enable']: self.wordcloud_record()
    except:
      warnf(f'[{module_name}]消息记录失败')

    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=2 and re.search(r'^消息功能$', self.rev_msg): self.help(auth)
      elif auth<=2 and re.search(r'词云', self.rev_msg): self.wordcloud(auth)
      elif auth<=2 and re.search(r'(\S+?)(又|也|同时)能?被?(称|叫)(为|做)?(\S+)', self.rev_msg): self.set_label()
      elif auth<=2 and re.search(r'(\S+)(说|言)(道|过)?(:|：)(\S+)', self.rev_msg): self.once_said()
      elif auth<=2 and re.search(r'^成员列表$', self.rev_msg): self.show_label()
      elif auth<=2 and re.search(r'(小本本|查看记录|记录列表)', self.rev_msg): self.read_record()
      elif auth<=2 and re.search(r'(撤回记录|删除记录|取消记录)', self.rev_msg): self.recall_record()
      elif auth<=2 and (re.search(r'\[CQ:reply,id=(-?[0-9]+)\]\s?\[CQ:at,qq=[0-9]+\]$', self.rev_msg) or self.rev_msg == ''): self.record()
      else: self.success = False
    else: self.success = False

  def help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=2:
      msg += '\n(打开|关闭)词云 |打开或关闭词云记录(默认关闭)'
      msg += '\n词云 (时间范围) |生成时间范围内你或此群的词云'
      msg += '\n词云形状 [形状代码] |更改词云形状'
      msg += '\n词云配色 [配色代码] |更改词云配色'
      msg += '\n[QQ账号或昵称]曾说过 |假装有人说过'
      msg += '\n[QQ账号或昵称]又叫做[称号] |记录成员的称号'
      msg += '\n成员列表 |查看记录在案的成员列表和称号'
      msg += '\n小本本 |查看消息记录'
      msg += '\n撤回记录 |撤回上一条消息记录'
      msg += '\n仅@不添加任何字符 |将你上一条消息记录在文档中'
    elif auth<=3:
      msg += '\n无帮助'

    reply(self.rev,msg)

  def record(self):
    if self.group_id == 0:
      msg = '仅支持在群内使用~'
      reply(self.rev, msg)
      return
    self.rev_msg = re.sub(r'\[CQ:at,qq=[0-9]+\]', '', self.rev_msg).strip()
    if re.search(r'\[CQ:reply,id=(-?[0-9]+)\]$', self.rev_msg):
      msg_id = re.search(r'\[CQ:reply,id=(-?[0-9]+)\]', self.rev_msg).groups()[0]
      record_msg(self.owner_id, get_msg({'message_id': msg_id}))
      msg = f'已成功记录此消息[CQ:reply,id={msg_id}]'
    elif self.rev_msg == '':
      history_msg = get_group_msg_history({'group_id':self.group_id})
      msg_id = 0
      for one_msg in history_msg[::-1][1:]:
        if one_msg['sender']['user_id'] == self.user_id:
          msg_id = one_msg['message_id']
          record_msg(self.owner_id, one_msg)
          msg = f'已成功记录此消息[CQ:reply,id={msg_id}]'
          break
      if not msg_id:
        self.success = False
        return
    else:
      self.success = False
      return
    reply(self.rev, msg)

  def read_record(self):
    msg = '好像没有消息记录哦呢~'
    history_msg = read_record_msg(self.owner_id)
    msg_list = []
    if history_msg:
      for one_msg in history_msg[::-1]:
        name = one_msg['nickname']
        uin = one_msg['user_id']
        content = one_msg['content']
        msg_list.insert(0, {'type': 'node', 'data': {'name': name, 'uin': uin, 'content': content}})
    if msg_list:
      msg = f'共有{len(msg_list)}条记录消息，正在整理~'
      reply(self.rev, msg)
      time.sleep(1)
      send_forward_msg(self.group_id, msg_list)
    else:
      reply(self.rev, msg)

  def recall_record(self):
    history_msg = read_record_msg(self.owner_id)
    if history_msg:
      history_msg.pop()
      save_json(f'{chat_log_dir}/{self.owner_id}.log', history_msg)
      msg = f'成功删除记录'
    else:
      msg = f'好像没有消息记录哦呢~'
    reply(self.rev, msg)

  def wordcloud_record(self):
    if re.search(r'(https?://|词云)', self.rev_msg): 
      return
    else:
      msg = re.sub(r'((\[|【|{)\S+(\]|】|})|\n|\s)', '', self.rev_msg)
      record_wordcloud(self.owner_id, msg)

  def wordcloud(self, auth):
    if re.search(r'(开启|启用|打开|记录|启动|关闭|禁用|取消)', self.rev_msg):
      if auth <= 1:
        self.wordcloud_switch()
        return
      else:
        msg = '你没有此操作的权限！'
    elif re.search(r'(图标|图案|蒙版|轮廓|形状|外形)', self.rev_msg):
      self.wordcloud_icon()
      return
    elif re.search(r'(主题|颜色|色彩|方案|配色)', self.rev_msg):
      self.wordcloud_palette()
      return
    else:
      wordcloud_file = f'{chat_log_dir}/wordcloud_{self.owner_id}.log'
      if self.config['wordcloud']['enable'] and os.path.exists(wordcloud_file):
        if re.search(r'(今天|今日)', self.rev_msg):
          msg = '正在生成今日词云...'
          text = read_wordcloud(self.owner_id, 'today')
        elif re.search(r'(昨天|昨日)', self.rev_msg):
          msg = '正在生成昨天词云...'
          text = read_wordcloud(self.owner_id, 'yesterday')
        elif re.search(r'(前天|前日)', self.rev_msg):
          msg = '正在生成前天词云...'
          text = read_wordcloud(self.owner_id, 'before_yesterday')
        elif re.search(r'(本周|这周|此周|这个?礼拜|这个?星期)', self.rev_msg):
          msg = '正在生成本周词云...'
          text = read_wordcloud(self.owner_id, 'this_week')
        elif re.search(r'(上周|上个?礼拜|上个?星期)', self.rev_msg):
          msg = '正在生成上周词云...'
          text = read_wordcloud(self.owner_id, 'last_week')
        elif re.search(r'(本月|这月|次月|这个月)', self.rev_msg):
          msg = '正在生成本月词云...'
          text = read_wordcloud(self.owner_id, 'this_month')
        elif re.search(r'(上个?月)', self.rev_msg):
          msg = '正在生成上个月词云...'
          text = read_wordcloud(self.owner_id, 'last_month')
        elif re.search(r'(今年|本年|此年|这一?年)', self.rev_msg):
          msg = '正在生成今年词云...'
          text = read_wordcloud(self.owner_id, 'this_year')
        elif re.search(r'(去年|上个?年)', self.rev_msg):
          msg = '正在生成去年词云...'
          text = read_wordcloud(self.owner_id, 'last_year')
        else:
          msg = '正在生成历史词云...'
          text = read_wordcloud(self.owner_id)
        if not text:
          msg = '没有消息记录哦~'
          reply(self.rev, msg)
          return
        if len(text) > 500:
          msg += '\n数据较多，请耐心等待~'
        reply(self.rev, msg)
        try:
          generate_wordcloud(self.config, text)
          msg = '[CQ:image,file=wordcloud.png]'
        except:
          msg = '生成错误！\n' + get_error(traceback.format_exc())
      elif not self.config['wordcloud']['enable']:
        msg = '请先开启开启词云记录哦~'
      else:
        msg = '没有任何词云记录哦~'
    reply(self.rev, msg)

  def wordcloud_switch(self):
    if re.search(r'(开启|启用|打开|记录|启动)', self.rev_msg):
      self.config['wordcloud']['enable'] = True
      msg = '词云记录已开启'
    elif re.search(r'(关闭|禁用|取消)', self.rev_msg):
      self.config['wordcloud']['enable'] = False
      msg = '词云记录已关闭'
    data_save(self.owner_id, self.config)
    reply(self.rev,msg)

  def wordcloud_icon(self):
    if re.search(r'#(\S+\s\S+)', self.rev_msg):
      icon = re.search(r'#(\S+\s\S+)', self.rev_msg).groups()[0]
      self.config['wordcloud']['icon'] = icon
      data_save(self.owner_id, self.config)
      msg = '词云形状设置成功！'
    else:
      msg = '请使用[#形状代码]来设置词云的形状,例如：“词云形状#fas fa-square”\n形状代码可以在https://fontawesome.com/icons获取'
    reply(self.rev,msg)

  def wordcloud_palette(self):
    if re.search(r'#(\S+)', self.rev_msg):
      palette = re.search(r'#(\S+)', self.rev_msg).groups()[0]
      self.config['wordcloud']['palette'] = palette
      data_save(self.owner_id, self.config)
      msg = '词云配色设置成功！'
    else:
      msg = '请使用[#配色代码]来设置词云的配色主题,例如：“词云主题#cartocolors.qualitative.Pastel_10”\n配色代码可以在https://jiffyclub.github.io/palettable获取'
    reply(self.rev,msg)

  def once_said(self):
    if self.group_id == 0:
      msg = '仅支持在群内使用~'
      reply(self.rev, msg)
      return
    msg_said = re.findall(r'(\S+)(说|言)(道|过)?(:|：)(\S+)', self.rev_msg)
    msg_list = []
    for said in msg_said:
      name = re.sub(r'曾?经?又?还?也?$', '', said[0])
      content = said[-1]
      uid = get_uid(self.config, name)
      if uid in self.config['users']:
        name = self.config['users'][uid]['nickname']
      elif name.isdigit():
        name = get_user_name(name)
      if re.search(r'^(我|吾|俺|朕|孤)$', name):
        name = self.user_name
        uid = self.user_id
      msg_list.append({'type': 'node', 'data': {'name': name, 'uin': uid, 'content': content}})
    if msg_list:
      send_forward_msg(self.group_id, msg_list)
    else:
      msg = '生成转发消息错误~'
      reply(self.rev, msg)

  def set_label(self):
    temp = re.search(r'(\S+?)(又|也|同时)能?被?(称|叫)(为|做)?(\S+)', self.rev_msg).groups()
    name = temp[0]
    label = temp[-1]
    msg = '好像没有找到这个用户欸~'
    if name.isdigit():
      info = get_stranger_info({'user_id':name})
      if status_ok(info):
        nickname = info['data']['nickname']
        msg = f'我记住了，{nickname}人送外号：{label}！'
        record_name(self.owner_id, name, nickname, label)
    elif re.search(r'^(我|吾|俺|朕|孤)$', name):
      msg = f'我记住了，{name}人送外号：{label}！'
      record_name(self.owner_id, self.user_id, self.user_name, label)
    else:
      for uid,user in self.config['users'].items():
        if name == uid or name == user['nickname']:
          record_name(self.owner_id, uid, name, label)
          msg = f'我记住了，{name}人送外号：{label}！'
          break
    reply(self.rev, msg)

  def show_label(self):
    msg = '========成员列表========'
    for uid,user in self.config['users'].items():
      msg += f'\nQQ：{uid}'
      msg += f'\n昵称：{user["nickname"]}'
      label = user['label'] if user["label"] else '无'
      msg += f'\n称号：{label}'
      msg += f'\n======================='
    reply(self.rev, msg)

  def user_record(self):
    if 'users' not in self.config:
      self.config['users'] = {}
    if str(self.user_id) not in self.config['users']:
      record_name(self.owner_id, self.user_id, self.user_name)

def data_save(owner_id, one_config):
  config[owner_id] = one_config
  save_json(data_file, config)

def record_name(owner_id, uid, name, label=''):
  config[owner_id]['users'][str(uid)] = {'nickname': name, 'label': label}
  data_save(owner_id, config[owner_id])

def record_msg(owner_id, msg):
  if 'data' in msg:
    msg = {'group_id': msg['data']['group_id'], 'time': msg['data']['time'], 'nickname': msg['data']['sender']['nickname'], 'user_id': msg['data']['sender']['user_id'], 'content': extract_content(msg['data']['message'])}
  elif 'raw_message' in msg:
    msg = {'group_id': msg['group_id'], 'time': msg['time'], 'nickname': msg['sender']['nickname'], 'user_id': msg['sender']['user_id'], 'content': extract_content(msg['raw_message'])}
  data_file = f'{chat_log_dir}/{owner_id}.log'
  all_record_msg_list = import_json(data_file)
  if not all_record_msg_list:
    all_record_msg_list = []
  all_record_msg_list.append(msg)
  save_json(data_file, all_record_msg_list)

def read_record_msg(owner_id):
  data_file = f'{chat_log_dir}/{owner_id}.log'
  all_record_msg_list = import_json(data_file)
  return all_record_msg_list

def extract_content(content, times=0):
  if times<=3 and re.search(r'\[CQ:forward,id=(\S+)\]', content):
    msg_id = re.search(r'\[CQ:forward,id=(\S+)\]', content).groups()[0]
    msg_list = read_forward_msg(msg_id)
    if msg_list:
      content_list = []
      for msg in msg_list:
        nickname = msg['sender']['nickname']
        user_id = msg['sender']['user_id']
        message = msg['content']
        content_list.append({'type': 'node', 'data': {'name': nickname, 'uin': user_id, 'content': extract_content(message, times+1)}})
      return content_list
    else:
      return content
  elif re.search(r'\[CQ:xml,data=(\S+)\]', content):
    desc = re.search(r'desc":"(\S+?)"', content).groups()[0]
    return f'[{desc}]XML无法解析'
  elif re.search(r'\[CQ:json,data=(\S+)\]', content):
    desc = re.search(r'desc":"(\S+?)"', content).groups()[0]
    return f'[{desc}]JSON无法解析'
  elif content == '你的QQ暂不支持查看&#91;转发多条消息&#93;，请期待后续版本。':
    return '[转发消息]无法记录迭代历史记录'
  else:
    return content

def record_wordcloud(owner_id, msg):
  data_file = f'{chat_log_dir}/wordcloud_{owner_id}.log'
  if not os.path.exists(data_file):
    open(data_file, mode='a', encoding='utf-8').write('')
  last_time = 0
  with open(data_file, mode='r', encoding='utf-8') as f:
    while temp := f.readline():
      if temp.strip().isdigit():
        last_time = temp.strip()
  now = int(time.mktime(datetime.date.today().timetuple()))
  if now > int(last_time):
    msg = f'{str(now)}\n{msg}'
    if last_time:
      msg = '\n' + msg
  open(data_file, mode='a', encoding='utf-8').write(msg)

def read_wordcloud(owner_id, type='all'):
  data_file = f'{chat_log_dir}/wordcloud_{owner_id}.log'
  log = {}
  with open(data_file, mode='r', encoding='utf-8') as f:
    line = f.readline().strip()
    timestamp = line if line.isdigit() else 0
    while line:
      if line.isdigit():
        timestamp = line
      elif timestamp != 0:
        log[timestamp] = log[timestamp] + line if timestamp in log else line
      line = f.readline().strip()
  text = ''
  today = datetime.date.today()
  if type == 'today':
    for timestamp,line in log.items():
      if time.mktime(today.timetuple()) <= int(timestamp):
        text += line
  elif type == 'yesterday':
    yesterday_start_time = time.mktime((today - datetime.timedelta(days=1)).timetuple())
    for timestamp,line in log.items():
      if yesterday_start_time <= int(timestamp) < time.mktime(today.timetuple()):
        text += line
  elif type == 'before_yesterday':
    yesterday_start_time = time.mktime((today - datetime.timedelta(days=1)).timetuple())
    before_yesterday_start_time = time.mktime((today - datetime.timedelta(days=2)).timetuple())
    for timestamp,line in log.items():
      if before_yesterday_start_time <= int(timestamp) < yesterday_start_time:
        text += line
  elif type == 'this_week':
    this_week_start_time = time.mktime((today - datetime.timedelta(days=today.weekday())).timetuple())
    for timestamp,line in log.items():
      if this_week_start_time <= int(timestamp):
        text += line
  elif type == 'last_week':
    this_week_start_time = time.mktime((today - datetime.timedelta(days=today.weekday())).timetuple())
    last_week_start_time = time.mktime((today - datetime.timedelta(days=today.weekday() + 7)).timetuple())
    for timestamp,line in log.items():
      if last_week_start_time <= int(timestamp) < this_week_start_time:
        text += line
  elif type == 'this_month':
    this_month_start_time = time.mktime((datetime.datetime(today.year, today.month, 1)).timetuple())
    for timestamp,line in log.items():
      if this_month_start_time <= int(timestamp):
        text += line
  elif type == 'last_month':
    this_month_start_time = time.mktime((datetime.datetime(today.year, today.month, 1)).timetuple())
    last_month_start_time = time.mktime((datetime.datetime(today.year, today.month, 1) - datetime.timedelta(30)).timetuple())
    for timestamp,line in log.items():
      if last_month_start_time <= int(timestamp) < this_month_start_time:
        text += line
  elif type == 'this_year':
    this_year_start_time = time.mktime((datetime.datetime(today.year, 1, 1)).timetuple())
    for timestamp,line in log.items():
      if this_year_start_time <= int(timestamp):
        text += line
  elif type == 'last_year':
    this_year_start_time = time.mktime((datetime.datetime(today.year, 1, 1)).timetuple())
    last_year_start_time = time.mktime(datetime.datetime(today.year - 1, 1, 1).timetuple())
    for timestamp,line in log.items():
      if last_year_start_time <= int(timestamp) < this_year_start_time:
        text += line
  else:
    for line in log.values():
      text += line
  return text

def generate_wordcloud(config, text):
  if not text: return
  stopwords = set()
  content = [line.strip() for line in open(stopwords_file, 'r', encoding='utf-8').readlines()]
  stopwords.update(content)

  text_list = ' '.join(jieba.lcut(text))

  image_file = gVar.data_dir + '/images/wordcloud.png'

  sc = stylecloud.gen_stylecloud(
    text = text_list,
    custom_stopwords = stopwords,
    size = 1024,
    gradient = 'horizontal',
    icon_name = config['wordcloud']['icon'],
    palette = config['wordcloud']['palette'],
    font_path = font_file,
    output_name = image_file)

def get_uid(config, name):
  if name in config['users']:
    return name
  for uid,user in config['users'].items():
    if name == user['nickname'] or name == user['label']:
      return uid
  if name.isdigit():
    return name
  return '10000'

module_enable(module_name, chat_log)
