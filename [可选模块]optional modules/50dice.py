#!/usr/bin/python
#骰娘模块处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

module_name = '骰娘模块'

class dice:
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
    if self.data and not hasattr(self.data,'sp_dice'):
      self.data.sp_dice = [1,2,3,4,5,6]

    #所有消息触发
    if auth<=3 and re.search(r'^\.rhelp$', self.rev_msg): self.dice_rhelp(auth)
    elif auth<=3 and re.search(r'^\.r$', self.rev_msg): self.dice_r()
    elif auth<=3 and re.search(r'^\.r\s?([0-9]+)?d\s?([0-9]+)?', self.rev_msg): self.dice_rd()
    elif auth<=3 and re.search(r'^\.ra', self.rev_msg): self.dice_ra()
    elif auth<=3 and re.search(r'^\.sr([0-9]+)?d', self.rev_msg): self.dice_srd()
    elif auth<=3 and re.search(r'^\.srv$', self.rev_msg): self.dice_srv()
    elif auth<=3 and re.search(r'^\.sr', self.rev_msg): self.dice_sr()
    else: self.success = False

  def dice_rhelp(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=3:
      msg += '\n可以对兼职骰娘的%ROBOT_NAME%使用以下指令：'
      msg += '\n.r |掷6面骰'
      msg += '\n.rXdY |掷X个Y面骰，X不填入默认为1'
      msg += '\n.ra [宾语][概率][主语] |掷100面骰进行事件判定'
      msg += '\n.sr A B C D E F |定义一个特殊6面骰，六个面的点数分别是ABCDEF'
      msg += '\n.srv |查看当前特殊6面骰'
      msg += '\n.srXd |掷X个特殊6面骰，X不填入默认为1'
    reply(self.rev,msg)

  def dice_r(self):
    msg =  self.user_name + '的掷骰结果是：' + str(random.randint(1,6))
    reply(self.rev,msg)

  def dice_rd(self):
    if re.search(r'^.r\s?([0-9]+)d\s?([0-9]+)', self.rev_msg):
      r = re.search(r'^.r\s?([0-9]+)d\s?([0-9]+)', self.rev_msg).groups()
      result_times = int(r[0])
      if (result_times > 10):
        msg = dialog.respond('!!骰子过多')
        reply(self.rev,msg)
      else:
        result_range = int(r[1])
        result = 0
        msg = self.user_name + '掷骰：'
        for i in range(1, result_times + 1):
          dice_once_result = random.randint(1, result_range)
          result = result + dice_once_result
          msg += str(dice_once_result)
          if (i < result_times):
            msg += ' '
        reply(self.rev,msg)
        time.sleep(1)
        msg = self.user_name + '的掷骰结果是：' + str(result_times) + 'D' + str(result_range) + '=' + str(result)
        reply(self.rev,msg)
    elif re.search(r'\.rd\s?[0-9]+', self.rev_msg):
      rd = re.search(r'\.rd\s?([0-9]+)', self.rev_msg).groups()
      result_range = int(rd[0])
      msg = self.user_name + '的掷骰结果是：D' + str(result_range) + '=' + str(random.randint(1,result_range))
      reply(self.rev,msg)
    else:
      msg = '请使用“.rhelp”获取帮助'
      reply(self.rev,msg)

  def dice_ra(self):
    if re.search(r'\.ra\s?(简单|容易|轻松|困难|极难)?[^0-9\s]+\s?[0-9]*\s?\S*', self.rev_msg):
      ra = re.search(r'\.ra\s?((简单|容易|轻松|困难|极难)?[^0-9\s]+)\s?([0-9]*)?\s?(\S*)', self.rev_msg).groups()
      skill_name = ra[0]
      win_rate = int(ra[2]) if ra[2] != '' else 50
      result = random.randint(1,100)
      nick_name = ra[3] if ra[3] != '' else self.user_name
      if not skill_name.find('轻松'):
        skill_name = skill_name.replace('轻松', '')
        win_rate = (win_rate + 100) / 2.0
      elif not skill_name.find('容易'):
        skill_name = skill_name.replace('容易', '')
        win_rate = (win_rate + 100) / 2.0
      elif not skill_name.find('简单'):
        skill_name = skill_name.replace('简单', '')
        win_rate = (win_rate + 100) / 2.0
      elif not skill_name.find('困难'):
        skill_name = skill_name.replace('困难', '')
        win_rate = win_rate / 2.0
      elif not skill_name.find('极难'):
        skill_name = skill_name.replace('极难', '')
        win_rate = win_rate / 5.0
      msg =  self.user_name + '掷骰：D100=' + str(result)
      reply(self.rev,msg)

      time.sleep(1)

      msg = nick_name + skill_name

      if (result<=win_rate):
        if (result <= 10):
          msg += '大'
        msg += '成功！'
      else:
        if (result >= 90):
          msg += '大'
        msg += '失败……'
      reply(self.rev,msg)
    else:
      msg = '请使用“.rhelp”获取帮助'
      reply(self.rev,msg)

  def dice_sr(self):
    if re.search(r'\.sr\s(-)?[0-9]+\s(-)?[0-9]+\s(-)?[0-9]+\s(-)?[0-9]+\s(-)?[0-9]+\s(-)?[0-9]+', self.rev_msg):
      msg = '特殊6面骰子已记忆：'
      for i in range(0,6):
        self.data.sp_dice[i] = int(self.rev_msg.split(' ')[i+1])
        msg += str(self.data.sp_dice[i])
        if (i < 5):
          msg += '|'
    else:
      msg = '请使用“.rhelp”获取帮助'
    reply(self.rev,msg)

  def dice_srd(self):
    if re.search(r'\.sr[0-9]+d', self.rev_msg):
      result_times = int(self.rev_msg.split('r')[1].split('d')[0])
      if (result_times > 10):
        msg = dialog.respond('!!骰子过多')
        reply(self.rev,msg)
      else:
        result = 0
        msg = self.user_name + '掷骰：'
        for i in range(1,result_times+1):
          dice_once_result = self.data.sp_dice[random.randint(0,5)]
          result = result + dice_once_result
          msg += str(dice_once_result)
          if (i < result_times):
            msg += ' '
        reply(self.rev,msg)

        time.sleep(1)
        msg = self.user_name + '的掷骰结果是：' + str(result)
        reply(self.rev,msg)
    else:
      msg =  self.user_name + '的掷骰结果是：' + str(self.data.sp_dice[random.randint(0,5)])
      reply(self.rev,msg)

  def dice_srv(self):
    msg = '目前正在使用的特殊6面骰子：'
    for i in range(0,6):
      msg += str(self.data.sp_dice[i])
      if (i < 5):
        msg += '|'
    reply(self.rev,msg)


module_enable(module_name, dice)