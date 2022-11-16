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
      config[self.owner_id] = {'wordcloud': False, 'icon': 'fas fa-square', 'palette': 'cartocolors.qualitative.Pastel_10”'}
    self.config = config[self.owner_id]

    if self.config['wordcloud']: self.record()
    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=2 and re.search(r'^消息功能$', self.rev_msg): self.help(auth)
      elif auth<=2 and re.search(r'词云', self.rev_msg): self.wordcloud()
      else: self.success = False
    else: self.success = False

  def help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=2:
      msg += '\n词云 (时间范围) |生成你或此群的词云'
      msg += '\n仅@不添加任何字符 |将你上一条消息记录在文档中'
    elif auth<=3:
      msg += '\n无帮助'

    reply(self.rev,msg)


  def record(self):
    if re.search(r'(https?://|词云)', self.rev_msg): 
      return
    else:
      msg = re.sub(r'(\[|【|{)\S+(\]|】|})', '', self.rev_msg)
      chat_log_add(self.owner_id, msg)

  def wordcloud(self):
    if re.search(r'(开启|启用|打开|记录|启动|关闭|禁用|取消)', self.rev_msg):
      self.wordcloud_switch()
    elif re.search(r'(图标|蒙版|轮廓|形状|外形)', self.rev_msg):
      self.wordcloud_icon()
    elif re.search(r'(主题|颜色|色彩|方案)', self.rev_msg):
      self.wordcloud_palette()
    else:
      chat_log_file = f'{chat_log_dir}/{self.owner_id}.log'
      if self.config['wordcloud'] and os.path.exists(chat_log_file):
        if re.search(r'(今天)', self.rev_msg):
          msg = '正在生成今天词云...'
          text = chat_log_read(self.owner_id, 'today')
        elif re.search(r'(昨天)', self.rev_msg):
          msg = '正在生成昨天词云...'
          text = chat_log_read(self.owner_id, 'yesterday')
        elif re.search(r'(前天)', self.rev_msg):
          msg = '正在生成前天词云...'
          text = chat_log_read(self.owner_id, 'before_yesterday')
        elif re.search(r'(本周|这周|此周|这礼拜)', self.rev_msg):
          msg = '正在生成本周词云...'
          text = chat_log_read(self.owner_id, 'this_week')
        elif re.search(r'(上周|上个礼拜)', self.rev_msg):
          msg = '正在生成上周词云...'
          text = chat_log_read(self.owner_id, 'last_week')
        elif re.search(r'(本月|这月|次月|这个月)', self.rev_msg):
          msg = '正在生成本月词云...'
          text = chat_log_read(self.owner_id, 'this_month')
        elif re.search(r'(上个月)', self.rev_msg):
          msg = '正在生成上个月词云...'
          text = chat_log_read(self.owner_id, 'last_month')
        elif re.search(r'(今年|这年|本年|这一年)', self.rev_msg):
          msg = '正在生成今年词云...'
          text = chat_log_read(self.owner_id, 'this_year')
        elif re.search(r'(去年)', self.rev_msg):
          msg = '正在生成去年词云...'
          text = chat_log_read(self.owner_id, 'last_year')
        else:
          msg = '正在生成词云...'
          text = chat_log_read(self.owner_id)
        if text:
          reply(self.rev, msg)
        else:
          msg = '还没有消息记录哦~'
          reply(self.rev, msg)
          return
        try:
          generate_wordcloud(self.config, text)
          msg = '[CQ:image,file=wordcloud.png]'
        except:
          msg = '生成错误！\n' + get_error(traceback.format_exc())
        time.sleep(1)
      elif not self.config['wordcloud']:
        msg = '请先开启开启词云记录哦~'
      else:
        msg = '还没有任何词云记录哦~'
      reply(self.rev, msg)

  def wordcloud_switch(self):
    if re.search(r'(开启|启用|打开|记录|启动)', self.rev_msg):
      self.config['wordcloud'] = True
      msg = '词云记录已开启'
    elif re.search(r'(关闭|禁用|取消)', self.rev_msg):
      self.config['wordcloud'] = False
      msg = '词云记录已关闭'
    data_save(self.owner_id, self.config)
    reply(self.rev,msg)

  def wordcloud_icon(self):
    if re.search(r'#(\S+\s\S+)', self.rev_msg):
      icon = re.search(r'#(\S+\s\S+)', self.rev_msg).groups()[0]
      self.config['icon'] = icon
      data_save(self.owner_id, self.config)
      msg = '词云轮廓设置成功！'
    else:
      msg = '请使用[#图标名]来设置词云的形状,例如：“词云形状#fas fa-square”\n形状可以在https://fontawesome.com/icons获取'
    reply(self.rev,msg)

  def wordcloud_palette(self):
    if re.search(r'#(\S+)', self.rev_msg):
      palette = re.search(r'#(\S+)', self.rev_msg).groups()[0]
      self.config['palette'] = palette
      data_save(self.owner_id, self.config)
      msg = '词云主题设置成功！'
    else:
      msg = '请使用[#主题]来设置词云的颜色主题,例如：“词云主题#cartocolors.qualitative.Pastel_10”\n主题可以在https://jiffyclub.github.io/palettable获取'
    reply(self.rev,msg)

def data_save(owner_id, one_config):
  config[owner_id] = one_config
  save_json(data_file, config)

def chat_log_add(owner_id, msg):
  data_file = f'{chat_log_dir}/{owner_id}.log'
  with open(data_file, mode='r', encoding='utf-8') as f:
    while temp := f.readline():
      last_time = temp
      f.readline()
  if time.mktime(datetime.date.today().timetuple()) > int(last_time):
    msg = f'\n{str(int(time.time()))}\n{msg}'
  open(data_file, mode='a', encoding='utf-8').write(msg)

def chat_log_read(owner_id, type='all'):
  data_file = f'{chat_log_dir}/{owner_id}.log'
  log = {}
  with open(data_file, mode='r', encoding='utf-8') as f:
    timestamp = f.readline()[:-1]
    while timestamp:
      log[timestamp] = f.readline()[:-1]
      timestamp = f.readline()[:-1]
  text = ''
  today = datetime.date.today()
  if type == 'today':
    for timestamp,line in log.items():
      if time.mktime(today.timetuple()) < int(timestamp):
        text += line
  elif type == 'yesterday':
    yesterday_start_time = time.mktime((today - datetime.timedelta(days=1)).timetuple())
    for timestamp,line in log.items():
      if yesterday_start_time < int(timestamp) < time.mktime(today.timetuple()):
        text += line
  elif type == 'before_yesterday':
    yesterday_start_time = time.mktime((today - datetime.timedelta(days=1)).timetuple())
    before_yesterday_start_time = time.mktime((today - datetime.timedelta(days=2)).timetuple())
    for timestamp,line in log.items():
      if before_yesterday_start_time < int(timestamp) < yesterday_start_time:
        text += line
  elif type == 'this_week':
    this_week_start_time = time.mktime((today - datetime.timedelta(days=today.weekday())).timetuple())
    for timestamp,line in log.items():
      if this_week_start_time < int(timestamp):
        text += line
  elif type == 'last_week':
    this_week_start_time = time.mktime((today - datetime.timedelta(days=today.weekday())).timetuple())
    last_week_start_time = time.mktime((today - datetime.timedelta(days=today.weekday() + 7)).timetuple())
    for timestamp,line in log.items():
      if last_week_start_time < int(timestamp) < this_week_start_time:
        text += line
  elif type == 'this_month':
    this_month_start_time = time.mktime((datetime.datetime(today.year, today.month, 1)).timetuple())
    for timestamp,line in log.items():
      if this_month_start_time < int(timestamp):
        text += line
  elif type == 'last_month':
    this_month_start_time = time.mktime((datetime.datetime(today.year, today.month, 1)).timetuple())
    last_month_start_time = time.mktime((datetime.datetime(today.year, today.month, 1) - datetime.timedelta(30)).timetuple())
    for timestamp,line in log.items():
      if last_month_start_time < int(timestamp) < this_month_start_time:
        text += line
  elif type == 'this_year':
    this_year_start_time = time.mktime((datetime.datetime(today.year, 1, 1)).timetuple())
    for timestamp,line in log.items():
      if this_year_start_time < int(timestamp):
        text += line
  elif type == 'last_year':
    this_year_start_time = time.mktime((datetime.datetime(today.year, 1, 1)).timetuple())
    last_year_start_time = time.mktime(datetime.datetime(today.year - 1, 1, 1).timetuple())
    for timestamp,line in log.items():
      if last_year_start_time < int(timestamp) < this_year_start_time:
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
    icon_name = config['icon'],
    palette = config['palette'],
    font_path = font_file,
    output_name = image_file)



module_enable(module_name, chat_log)