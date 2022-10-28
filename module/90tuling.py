#!/usr/bin/python
#图灵机器人模块处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

module_name = '图灵机器人模块'

api_key = ''

class tuling:
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
    # if self.group_id:
    #   self.owner_id = f'g{self.group_id}'
    # else:
    #   self.owner_id = f'u{self.user_id}'
    # self.data = gVar.data[self.owner_id]

    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=2: self.tuling()
      else: self.success = False
    else: self.success = False

  def tuling(self):
    msg = get_tuling(self.rev_msg, self.user_id, self.group_id, self.user_name)
    reply(self.rev,msg)
    
def get_tuling(info, user_id, group_id, user_name):
  post_json = {
    "reqType": 0,
    "perception": {
      "inputText": {
        "text": info
      },
    },
    "userInfo": {
      "apiKey": api_key,
      "userId": user_id,
      "groupId": group_id,
      "userIdName": user_name
    }
  }
  if re.search(r'^\[CQ:image,.*\]$',info):
    post_json['reqType'] = 1
  elif re.search(r'\[CQ:image,.*\]',info):
    post_json['perception']['inputText']['text'] = re.sub(r'\[CQ:image.*\]', '', post_json['perception']['inputText']['text'])
  if gVar.is_debug: printf(f'调用图灵机器人API返回结果：{post_json}')
  dat = json.dumps(post_json)
  url = 'http://openapi.turingapi.com/openapi/api/v2'
  response = requests.post(url, data=dat).json()
  return response['results'][0]['values']['text']


if api_key == '':
  warnf(f'[{module_name}] 模块已禁用，如需启用请先前往[https://www.tuling123.com/]获取APIKey')
else:
  module_enable(module_name, tuling)