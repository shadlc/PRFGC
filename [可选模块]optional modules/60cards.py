#!/usr/bin/python
#卡牌模块处理


import global_variable as gVar
from ifunction import *
from api_cqhttp import *

module_name = '卡牌模块'

vup_standard_deck = ["杀[♠7]","杀[♠8]","杀[♠8]","杀[♠9]","杀[♠9]","杀[♠10]","杀[♠10]","杀[♣2]","杀[♣3]","杀[♣4]","杀[♣5]","杀[♣6]","杀[♣7]","杀[♣8]","杀[♣8]","杀[♣9]","杀[♣9]","杀[♣10]","杀[♣10]","杀[♣J]","杀[♣J]","杀[♥10]","杀[♥10]","杀[♥J]","杀[♦6]","杀[♦7]","杀[♦8]","杀[♦9]","杀[♦10]","杀[♦K]","闪[♥2]","闪[♥2]","闪[♥K]","闪[♥8]","闪[♥9]","闪[♥J]","闪[♥Q]","闪[♦2]","闪[♦2]","闪[♦3]","闪[♦4]","闪[♦5]","闪[♦6]","闪[♦7]","闪[♦8]","闪[♦9]","闪[♦10]","闪[♦J]","闪[♦J]","闪[♦6]","闪[♦7]","闪[♦8]","闪[♦10]","闪[♦J]""桃[♥3]","桃[♥4]","桃[♥5]","桃[♥6]","桃[♥6]","桃[♥7]","桃[♥8]","桃[♥9]","桃[♥Q]","桃[♦Q]","桃[♦2]","桃[♦3]","诸葛连弩[♣A]","诸葛连弩[♦A]","雌雄双股剑MK2[♠2]","青釭剑[♠6]","青龙偃月刀[♠5]","丈八蛇矛[♠Q]","贯石斧[♦5]","方天画戟[♦Q]","麒麟弓[♥5]","八卦阵[♠2]","八卦阵[♣2]","绝影[♠5]","的卢[♣5]","爪黄飞电[♥K]","赤兔[♥5]","大宛[♠K]","紫骍[♦K]","骅骝[♦K]","五谷丰登[♥3]","五谷丰登[♥4]","桃园结义[♥A]","南蛮入侵[♠7]","南蛮入侵[♠K]","南蛮入侵[♣7]","万箭齐发[♥A]","决斗[♠A]","决斗[♣A]","决斗[♦A]","无中生有[♥7]","无中生有[♥8]","无中生有[♥9]","无中生有[♥J]","顺手牵羊[♠3]","顺手牵羊[♠4]","顺手牵羊[♠J]","顺手牵羊[♦3]","顺手牵羊[♦4]","过河拆桥[♠3]","过河拆桥[♠4]","过河拆桥[♠Q]","过河拆桥[♣3]","过河拆桥[♣4]","过河拆桥[♦Q]","借刀杀人[♣Q]","借刀杀人[♣K]","无懈可击[♠J]","无懈可击[♣Q]","无懈可击[♣K]","无懈可击[♥A]","无懈可击[♥K]","乐不思蜀[♥6]","乐不思蜀[♠6]","乐不思蜀[♣6]","闪电[♠A]","闪电[♥A]","寒冰剑[♠2]","仁王盾[♣2]","无懈可击[♦Q]","古锭刀[♠A]","藤甲[♠2]","藤甲[♣2]","兵粮寸断[♠10]","兵粮寸断[♠8]","兵粮寸断[♣4]","白银狮子[♣A]","朱雀羽扇[♦A]","雪年糕棍[♣K]","宇航兔[♣7]","两轮车[♦7]","藏宝图[♠A]","十字架[♥J]","银月枪[♦Q]","铁索连环[♠J]","铁索连环[♠Q]","铁索连环[♠K]","铁索连环[♣10]","铁索连环[♣J]","铁索连环[♣Q]","铁索连环[♣K]","火攻[♥2]","火攻[♥3]","火攻[♦Q]","釜底抽薪[♥5]","釜底抽薪[♦5]","酒[♠3]","酒[♠9]","酒[♣3]","酒[♣9]","酒[♦9]","雷杀[♠4]","雷杀[♠5]","雷杀[♠6]","雷杀[♠7]","雷杀[♠8]","雷杀[♣5]","雷杀[♣6]","冰杀[♣7]","冰杀[♣8]","火杀[♥4]","火杀[♥7]","火杀[♥10]","火杀[♦4]","火杀[♦5]"]
class cards:
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
    if self.data and not hasattr(self.data,'deck'):
      self.data.deck = vup_standard_deck[:]

    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=3 and re.search(r'^卡牌功能$',self.rev_msg): self.card_help(auth)
      elif auth<=3 and re.search(r'^判定$',self.rev_msg): self.judge()
      elif auth<=3 and re.search(r'^查看牌堆$',self.rev_msg): self.check()
      elif auth<=3 and re.search(r'^洗牌$',self.rev_msg): self.shuffle()
      elif auth<=3 and re.search(r'^(请)?发牌(！|!)?',self.rev_msg): self.deal()
      elif auth<=3 and re.search(r'^闪电对决',self.rev_msg): self.lightning_duel()
      else: self.success = False
    else: self.success = False


  def card_help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=3:
      msg += '\n发牌 |从牌堆发牌'
      msg += '\n[事件]判定 |对某事件进行判定'
      msg += '\n闪电对决 |进行多人闪电对决'
      msg += '\n洗牌 |对牌堆进行洗牌'
      msg += '\n查看牌堆 |查看牌堆卡牌张数'
    reply(self.rev,msg)

  def judge(self):
    msg = self.user_name + '的判定结果是：' + drawCard(self.data.deck)
    reply(self.rev,msg)

  def check(self):
    msg = '牌堆中还有' + str(len(self.data.deck)) + '张牌'
    reply(self.rev,msg)

  def shuffle(self):
    refresh(self.data.deck)
    msg = '姬姬已洗牌，牌堆现有' + str(len(self.data.deck)) + '张牌'
    reply(self.rev,msg)

  def deal(self):
    if re.search(r'^(请|!|！)',self.rev_msg) or random.randint(0,5) >= 1:
      if re.search(r'(请)?发牌(！|!)?\s?([0-9]+)',self.rev_msg):
        result_range = int(re.search(r'发牌\s?([0-9]+)',self.rev_msg).groups()[0])
        if random.randint(0,10) + result_range > 30:
          msg = QA_get('!!发牌过多')
          reply(self.rev,msg)
        else:
          cards_str = ""
          for i in range(1, result_range):
            cards_str = cards_str + drawCard(self.data.deck) + ','
          cards_str = cards_str + drawCard(self.data.deck)
          
          msg = '姬姬发牌：' + cards_str
          reply(self.rev,msg)
      else:
        msg = '姬姬发牌：' + drawCard(self.data.deck)
        reply(self.rev,msg)
    else:
      msg = '想要姬姬发牌的话要说“请发牌”！'
      reply(self.rev,msg)

  def lightning_duel(self):
    if re.search(r'闪电对决(\s\S*)*', self.rev_msg):
      player_list = []

      if re.search(r'闪电对决(\s\S*)+', self.rev_msg):
        for i in re.findall(r'(?<=\s)[^(闪电对决)\s]+', self.rev_msg):
          player_list.append(i)
      else:
        player_list = [gVar.self_name, self.user_name]

      lightning_at = random.randint(0,len(player_list)-1)
      max_times = max(10, 3*len(player_list))
      lightning_counter = 0

      msg = f'{len(player_list)}名角色参与闪电对决！\n本次对决从{player_list[lightning_at]}开始~'
      reply(self.rev,msg)

      time.sleep(1)
      msg = ''
      for i in range(max_times):
        rand_card = drawCard(self.data.deck)
        if isLightningCard(rand_card):
          msg += player_list[lightning_at] + '最终判定：' + rand_card
          break
        else:
          msg += player_list[lightning_at] + '判定：' + rand_card + '\n'
        lightning_at = lightning_at + 1 if (lightning_at < len(player_list)-1) else 0
        lightning_counter += 1
      reply(self.rev,msg.strip())
      
      time.sleep(1)
      if lightning_counter >= max_times:
        msg= QA_get('!!无人受伤')
      else:
        if player_list[lightning_at] != gVar.self_name:
          msg = gVar.self_name + '对' + player_list[lightning_at] + '造成3点雷电伤害！ (°∀°)ﾉ'
        else:
          msg = self.user_name + '对' + player_list[lightning_at] + '造成3点雷电伤害，哭唧唧~（/TДT)/'
      reply(self.rev,msg)


def isLightningCard(card):
  if "♠" in card and card[-2] in ['2','3','4','5','6','7','8','9']:
    return True
  return False

def refresh(draw_pile):
  draw_pile.clear()
  for i in vup_standard_deck:
    draw_pile.append(i)

def drawCard(draw_pile):
  if (len(draw_pile) == 0):
    refresh(draw_pile)
  result = random.choice(draw_pile)
  draw_pile.remove(result)
  return result



module_enable(module_name, cards)