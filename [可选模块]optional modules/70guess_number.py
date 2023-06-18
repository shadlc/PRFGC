#!/usr/bin/python
#数字模块处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

module_name = '猜数字模块'

class guess_number:
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
    if self.data and not hasattr(self.data,'guess_for_player'):
      self.data.guess_for_player = [False, 50, 0] #是否开始猜 正确数字 次数
      self.data.guess_for_robot = [False, 0, 100, 0, 50] #是否开始猜 下界 上界 次数 上次猜的数字

    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=3 and re.search(r'^数字功能$', self.rev_msg): self.guess_help(auth)
      elif auth<=3 and re.search(r'^猜数字$', self.rev_msg): self.player_start_guess()
      elif auth<=3 and re.search(r'^姬姬猜数字$', self.rev_msg): self.robot_start_guess()
      elif auth<=3 and re.search(r'正确$', self.rev_msg) and self.data.guess_for_robot[0] == True: self.correct()
      elif auth<=3 and re.search(r'小了$', self.rev_msg) and self.data.guess_for_robot[0] == True: self.too_small()
      elif auth<=3 and re.search(r'大了$', self.rev_msg) and self.data.guess_for_robot[0] == True: self.too_big()
      elif auth<=3 and re.search(r'[0-9]+$', self.rev_msg) and self.data.guess_for_player[0] == True: self.guess_num()
      elif auth<=3 and re.search(r'(我不玩|不玩)', self.rev_msg) and (self.data.guess_for_player[0] == True or self.data.guess_for_robot[0] == True): self.dont_play()
      else: self.success = False
    #群聊非@消息触发
    elif self.group_id:
      if auth<=3 and re.search(r'正确$', self.rev_msg) and self.data.guess_for_robot[0] == True: self.correct()
      elif auth<=3 and re.search(r'小了$', self.rev_msg) and self.data.guess_for_robot[0] == True: self.too_small()
      elif auth<=3 and re.search(r'大了$', self.rev_msg) and self.data.guess_for_robot[0] == True: self.too_big()
      elif auth<=3 and re.search(r'[0-9]+$', self.rev_msg) and self.data.guess_for_player[0] == True: self.guess_num()
      elif auth<=3 and re.search(r'(我不玩|不玩)', self.rev_msg) and (self.data.guess_for_player[0] == True or self.data.guess_for_robot[0] == True): self.dont_play()
      else: self.success = False
    else: self.success = False

  def guess_help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=3:
      msg += '\n猜数字 |猜一个1~100的数字'
      msg += '\n姬姬猜数字 |让姬姬猜一个1~100的数字'
    reply(self.rev,msg)

  def player_start_guess(self):
    self.data.guess_for_player = [True, random.randint(0, 100), 0]
    msg = '%ROBOT_NAME%想了一个0~100之间的整数，来猜猜看吧'
    reply(self.rev,msg)
    printf('随机数字为' + str(self.data.guess_for_player[1]))

  def robot_start_guess(self):
    self.data.guess_for_robot = [True, 0, 100, 1, 50]
    msg = '你想一个0~100之间的整数，%ROBOT_NAME%来猜！\n请用“大了”、“小了”、“正确”这三种指令回答我，不许变卦哦！'
    reply(self.rev,msg)
    time.sleep(1)
    msg = QA_get('!!机智如我') + '决定先从50开始猜！'
    reply(self.rev,msg)

  def guess_num(self):
    guess_num = int(re.search(r'([0-9]+)$', self.rev_msg).groups()[0])
    self.data.guess_for_player[2] += 1
    times = self.data.guess_for_player[2]
    number = self.data.guess_for_player[1]
    if guess_num == number:
      self.data.guess_for_player[0] = False
      msg = self.user_name + f'猜对啦！\n一共花了{times}次，'
      if times >= 11 :
        msg = msg + '不太聪明的样子'
      elif times >= 7 :
        msg = msg + '稍微有点可惜呢'
      elif times >= 4 :
        msg = msg + '奖励一朵小红花~'
      else:
        msg = msg + '读心术大师就是你吗？'
    elif guess_num < number:
      msg = '%ROBOT_NAME%想的数字比'+str(guess_num)+'大'
      if abs(guess_num - number) >= 40 :
        msg = msg + '非常多！'
      elif abs(guess_num - number) >= 16 :
        msg = msg + '哦'
      elif abs(guess_num - number) >= 8 :
        msg = msg + '一点'
      else:
        msg = msg + '一点点'
    elif guess_num > number:
      msg = '%ROBOT_NAME%想的数字比'+str(guess_num)+'小'
      if abs(guess_num - number) >= 40 :
        msg = msg + '非常多！'
      elif abs(guess_num - number) >= 16 :
        msg = msg + '哦'
      elif abs(guess_num - number) >= 8 :
        msg = msg + '一点'
      else:
        msg = msg + '一点点'
    reply(self.rev,msg)

  def correct(self):
    times = self.data.guess_for_robot[3]
    msg = f'好耶！%ROBOT_NAME%猜了{times}次，'
    if times >= 11 :
      msg = msg + '不可能吧！'
    elif times >= 7 :
      msg = msg + '正常水平啦'
    elif times >= 4 :
      msg = msg + '我可是天才~'
    else:
      msg = msg + '你真的没有在哄我吗？\n(灬ºωº灬)'
    reply(self.rev,msg)

  def too_small(self):
    self.data.guess_for_robot[3] = self.data.guess_for_robot[3] + 1
    if self.data.guess_for_robot[1] != self.data.guess_for_robot[2] and self.data.guess_for_robot[1] < self.data.guess_for_robot[4]:
      self.data.guess_for_robot[4] = random.randint(self.data.guess_for_robot[1], self.data.guess_for_robot[2])
      self.data.guess_for_robot[1] = self.data.guess_for_robot[4] + 1
      msg = QA_get('!!猜开头词') + str(self.data.guess_for_robot[4]) + QA_get('!!猜结束词')
    else:
      self.data.guess_for_robot[0] = False
      msg = QA_get('!!你耍赖')
    reply(self.rev,msg)

  def too_big(self):
    self.data.guess_for_robot[3] = self.data.guess_for_robot[3] + 1
    if self.data.guess_for_robot[1] != self.data.guess_for_robot[2] and self.data.guess_for_robot[2] > self.data.guess_for_robot[4]:
      printf(str(self.data.guess_for_robot))
      self.data.guess_for_robot[4] = random.randint(self.data.guess_for_robot[1], self.data.guess_for_robot[2])
      self.data.guess_for_robot[2] = self.data.guess_for_robot[4] - 1
      msg = QA_get('!!猜开头词') + str(self.data.guess_for_robot[4]) + QA_get('!!猜结束词')
    else:
      self.data.guess_for_robot[0] = False
      msg = QA_get('!!你耍赖')
    reply(self.rev,msg)

  def dont_play(self):
    self.data.guess_for_player[0] = False
    self.data.guess_for_robot[0] = False 
    msg = QA_get('!!无奈')
    reply(self.rev,msg)



module_enable(module_name, guess_number)