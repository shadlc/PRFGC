#!/usr/bin/python
#复读机模块专用处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

module_name = '复读机模块'

data_file = 'data/repeater_data.json'
config = import_json(data_file)

class repeater:
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
    self.data = gVar.data[self.owner_id]
    if self.owner_id not in config:
      config[self.owner_id] = {'repeat': True}
    self.config = config[self.owner_id]

    #预处理消息（图片消息链接处理）
    if 'message' in self.rev:
      self.rev_msg = re.sub(r',url=.*?]',']', self.rev_msg)

    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=1 and re.search(r'^(开启|关闭)?复读机$', self.rev_msg): self.setting()
      else: self.success = False
    #群聊非@消息触发
    elif self.group_id and not gVar.at_info in self.rev_msg:
      if auth<=3 and self.config['repeat'] and re.sub(r',url=.*?]',']', str(self.data.past_message)).count(f"'message': '{self.rev_msg}")>1: self.repeat()
      else: self.success = False
    else: self.success = False

  def repeat(self):
    printf(f'{LBLUE}[RECEIVE]{RESET}在群{LPURPLE}{self.group_name}({self.group_id}){RESET}检测到来自{LPURPLE}{self.user_name}({self.user_id}){RESET}的多次复读：{self.rev_msg}')
    if str(self.data.past_message).count("Already_Repeat"):
      printf('短时间内已复读过，不再进行复读')
      self.success = False
    else:
      repeat_count = re.sub(r',url=.*?]',']', str(self.data.past_message)).count(f"'message': '{self.rev_msg}'")
      printf('本次复读概率为' + str(round((5/(11-repeat_count))*100,2)) + '%')
      if random.randint(0,10-repeat_count) < 5:
        self.data.past_message[-1]['message'] += 'Already_Repeat'
        msg = self.rev_msg
        reply(self.rev,msg)
        printf('复读成功 o((>ω< ))o')
      else:
        printf('复读失败/(ㄒoㄒ)/')

  def setting(self):
    flag = self.config['repeat']
    text = '开启' if self.config['repeat'] else '关闭'
    if re.search(r'(开启|打开|启用|允许)', self.rev_msg):
      flag = True
      text = '开启'
    elif re.search(r'(关闭|禁止|不允许|取消)', self.rev_msg):
      flag = False
      text = '关闭'
    msg = f'复读机功能已{text}'
    self.config['repeat'] = flag
    data_save(self.owner_id, self.config)
    reply(self.rev,msg)

def data_save(owner_id, one_config):
  config[owner_id] = one_config
  save_json(data_file, config)



module_enable(module_name, repeater)