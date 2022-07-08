#!/usr/bin/python
#机器人基础通知处理模块

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

function_name = '基础通知处理模块'
gVar.functions.append(function_name)
printf(f'{LYELLOW}{function_name}已接入！{RESET}',console=False)

class notice(object):
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
		self.notice_time = self.rev['time'] if 'time' in self.rev else 0

		#初始化此模块需要的数据
		if self.group_id:
			self.data = gVar.data['g' + str(self.group_id)]
		else:
			self.data = gVar.data['u' + str(self.user_id)]

		if self.notice_type == 'notify' and self.sub_type == 'poke' and self.user_id != gVar.self_id: self.poke()
		elif self.notice_type == 'friend_recall': self.friend_recall()
		elif self.notice_type == 'group_recall': self.group_recall()
		elif self.notice_type == 'group_upload': self.group_upload()
		elif self.notice_type == 'group_admin': self.group_admin()
		elif self.notice_type == 'group_decrease': self.group_decrease()
		elif self.notice_type == 'group_increase': self.group_increase()
		elif self.notice_type == 'group_ban': self.group_ban()
		elif self.notice_type == 'friend_add': self.friend_add()
		else: self.success = False

	def poke(self):
		if self.group_id:
			printf(f'{LYELLOW}[NOTICE]在群{LPURPLE}{self.group_name}({self.group_id}){RESET}接收来自{LPURPLE}{self.user_name}({self.user_id}){RESET}的戳一戳')
			msg = '[CQ:poke,qq=' + str(self.user_id) + ']'
			reply_id('group', self.group_id, msg)
		else:
			printf(f'{LYELLOW}[NOTICE]接收来自{LPURPLE}{self.user_name}({self.user_id}){RESET}的戳一戳')
			msg = '[CQ:poke,qq=' + str(self.user_id) + ']'
			reply_id('private', self.user_id, msg)
		printf(f'尝试对{LPURPLE}{self.user_name}({self.user_id}){RESET}进行反戳')

	def friend_recall(self):
		msg = QA_get('!!对方撤回')
		reply_id('private', self.user_id, msg)

	def group_recall(self):
		printf(f'在群{LPURPLE}{self.group_name}({self.group_id}){RESET}检测到一条撤回消息')
		recall_time = time.strftime("%Y年%m月%d日%H:%M:%S", time.localtime(self.notice_time))
		recall_message = None
		if self.user_id == gVar.self_id and self.operator_id != gVar.self_id:
			msg = f'{self.operator_name}在{recall_time}将我的消息撤回，我很难过'
		elif self.user_id != gVar.self_id:
			for message in self.data.past_message:
				if 'message_id' in message and self.msg_id == message['message_id']:
					recall_message = message['raw_message']
			if recall_message != None:
				msg = f'{self.operator_name}在{recall_time}试图将{self.user_name}的一条消息 “{recall_message}” 撤回，我还记得'
			else:
				msg = f'{self.operator_name}在{recall_time}将{self.user_name}的一条消息撤回，但是我记不得了...'
		reply_id('group', self.group_id, msg)

	def group_upload(self):
		file_name = self.rev['file']['name']
		file_size = calc_size(self.rev['file']['size'])
		printf(f'{LYELLOW}[NOTICE]{RESET}群{LPURPLE}{self.group_name}({self.group_id}){RESET}内{LPURPLE}{self.user_name}({self.user_id}){RESET}上传了文件{LYELLOW}{file_name}({file_size})')

	def group_admin(self):
		if self.sub_type == 'set':
			printf(f'{LYELLOW}[NOTICE]{RESET}群{LPURPLE}{self.group_name}({self.group_id}){RESET}内{LPURPLE}{self.user_name}({self.user_id}){RESET}被设为管理员')
		elif self.sub_type == 'unset':
			printf(f'{LYELLOW}[NOTICE]{RESET}群{LPURPLE}{self.group_name}({self.group_id}){RESET}内管理员{LPURPLE}{self.user_name}({self.user_id}){RESET}被取缔')

	def group_decrease(self):
		if self.sub_type == 'leave':
			printf(f'{LYELLOW}[NOTICE]{RESET}{LPURPLE}{self.user_name}({self.user_id}){RESET}主动退群{LPURPLE}{self.group_name}({self.group_id}){RESET}')
		elif self.sub_type == 'kick':
			printf(f'{LYELLOW}[NOTICE]{RESET}{LPURPLE}{self.user_name}({self.user_id}){RESET}被踢出群{LPURPLE}{self.group_name}({self.group_id}){RESET}')

	def group_increase(self):
		if self.sub_type == 'approve':
			printf(f'{LYELLOW}[NOTICE]{RESET}{LPURPLE}{self.user_name}({self.user_id}){RESET}已被同意加入群{LPURPLE}{self.group_name}({self.group_id}){RESET}')
		elif self.sub_type == 'invite':
			printf(f'{LYELLOW}[NOTICE]{RESET}{LPURPLE}{self.user_name}({self.user_id}){RESET}已被邀请加入群{LPURPLE}{self.group_name}({self.group_id}){RESET}')

	def group_ban(self):
		duration = self.rev['duration']
		if duration: duration = duration + '秒' if int(duration) < 268435455 else '永久'
		if self.user_id == 0:
			if self.sub_type == 'ban':
				printf(f'{LYELLOW}[NOTICE]{RESET}群{LPURPLE}{self.group_name}({self.group_id}){RESET}内{LPURPLE}{self.operator_name}({self.operator_id}){RESET}设置了{LYELLOW}{duration}{RESET}的全员禁言')
			elif self.sub_type == 'lift_ban':
				printf(f'{LYELLOW}[NOTICE]{RESET}群{LPURPLE}{self.group_name}({self.group_id}){RESET}内{LPURPLE}{self.operator_name}({self.operator_id}){RESET}解除了全员禁言')
		else:
			if self.sub_type == 'ban':
				printf(f'{LYELLOW}[NOTICE]{RESET}群{LPURPLE}{self.group_name}({self.group_id}){RESET}内{LPURPLE}{self.operator_name}({self.operator_id}){RESET}为{LPURPLE}{self.user_name}({self.user_id}){RESET}设置了{LYELLOW}{duration}秒{RESET}的禁言')
			elif self.sub_type == 'lift_ban':
				printf(f'{LYELLOW}[NOTICE]{RESET}群{LPURPLE}{self.group_name}({self.group_id}){RESET}内{LPURPLE}{self.operator_name}({self.operator_id}){RESET}解除了{LPURPLE}{self.user_name}({self.user_id}){RESET}的禁言')

	def friend_add(self):
		printf(f'{LYELLOW}[NOTICE]{RESET}{LPURPLE}{self.user_name}({self.user_id}){RESET}已加为好友')