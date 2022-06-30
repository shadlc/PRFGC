#!/usr/bin/python
#机器人基础消息处理模块

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

function_name = '基础消息处理模块'
gVar.functions.append(function_name)
printf(f'{LYELLOW}{function_name}已接入！{RESET}',console=False)

class message(object):
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

		#群聊@消息以及私聊消息触发
		if not self.group_id or gVar.at_info in self.rev_msg:
			if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'')
			if re.search(r'^权限(等级)?$', self.rev_msg): self.authority(auth)
			elif re.search(r'^(增加|添加|删除|取消)?管理员\s?[0-9]+', self.rev_msg) and auth<=1: self.admin()
			elif re.search(r'^(撤回|闭嘴|嘘)(！|，)?(懂？)?$', self.rev_msg) and auth<=1: self.recall() 
			elif re.search(r'^重启$', self.rev_msg) and auth<=1: self.restart()
			elif re.search(r'^计时\s?[0-9]+', self.rev_msg) and auth<=2: self.delay()
			elif re.search(r'^测试', self.rev_msg) and auth<=2: self.test()
			elif re.search(r'^信息$', self.rev_msg) and auth<=1: self.info()
			elif re.search(r'^语音\s?\S*', self.rev_msg) and auth<=2: self.voice()
			elif re.search(r'^向?群?([0-9]+)?说\s?\S+$', self.rev_msg) and auth<=2: self.say()
			elif re.search(r'^(开启|关闭)?调试(模式)?$', self.rev_msg) and auth<=1: self.debug()
			elif re.search(r'^(开启|关闭)?静默(模式)?$', self.rev_msg) and auth<=1: self.slience()
			elif re.search(r'(小|新|学|增加|添加|增添)(知识|问答|回答|对话)', self.rev_msg): self.QA_new()
			elif QA_contains(self.rev_msg.replace('!!','')): self.QA_reply()
			else: self.success = False
		else: self.success = False

	def admin(self):
		if re.search(r'^(增加|添加)管理员', self.rev_msg):
			number = re.search(r'^(增加|添加)管理员([0-9]+)', self.rev_msg).groups()[1]
			if number not in gVar.admin_id:
				gVar.admin_id.append(number)
				write_config('Data','Op',str(gVar.admin_id).strip('[]').replace('\'',''))
				printf(f'{LPURPLE}{get_user_name(number)}({number}){RESET}已设置为管理员')
				msg = f'{get_user_name(number)}({number})已设置为管理员'
			else:
				warnf(f'{LPURPLE}{user_name}({user_id}){RESET}已经是管理员！')
				msg = f'{get_user_name(number)}({number})已经是管理员！'

		elif re.search(r'^(删除|取消)管理员', self.rev_msg):
			number = re.search(r'^(删除|取消)管理员([0-9]+)', self.rev_msg).groups()[1]
			if number in gVar.admin_id:
				gVar.admin_id.remove(number)
				write_config('Data','Op',str(gVar.admin_id).strip('[\'\']').replace('\'',''))
				printf(f'{LPURPLE}{get_user_name(number)}({number}){RESET}不再是管理员')
				msg = f'{get_user_name(number)}({number})不再是管理员'
			else:
				warnf(f'{LPURPLE}{user_name}({user_id}){RESET}不是管理员！')
				msg = f'{get_user_name(number)}({number})不是管理员！'
		else:
			msg = '请使用 [增加|删除]管理员 [QQ号] 进行增添管理员'
		reply(self.rev,msg,True)

	def authority(self,auth):
		if auth == 0 : auth_level = '后台权限'
		elif auth == 1 : auth_level = '管理员权限'
		elif auth == 2 : auth_level = '全功能权限'
		elif auth == 3 : auth_level = '陌生人权限'
		else: auth_level = '未知权限'
		msg = f'您的权限等级为：{auth_level}'
		reply(self.rev,msg)

	def debug(self):
		if re.search(r'^开启', self.rev_msg):
			gVar.is_debug = True
		elif re.search(r'^关闭', self.rev_msg):
			gVar.is_debug = False
		else:
			gVar.is_debug = not gVar.is_debug
		write_config('Data','SlienceMode',gVar.is_debug)
		if gVar.is_debug:
			msg = '调试模式已开启'
		else:
			msg = '调试模式已关闭'
		warnf('调试模式已开启') if gVar.is_debug else warnf('调试模式已关闭')
		reply(self.rev,msg,True)

	def delay(self):
		sleep_time = int(re.search(r'([0-9]+)', self.rev_msg).groups()[0])
		msg = '计时' + str(sleep_time) + '秒开始'
		reply(self.rev,msg)
		time.sleep(sleep_time)
		msg = '计时' + str(sleep_time) + '秒结束'
		reply(self.rev,msg)

	def info(self):
		info = get_version_info()
		msg = '=======CQHTTP版本信息======='
		msg += (f'\n内部应用名称：{info["app_name"]}')
		msg += (f'\n版本号：{info["app_version"]}')
		msg += (f'\n运行平台：{info["runtime_os"]}')
		msg += (f'\n登陆设备：{info["device"]}')
		msg += (f'\n==========变量信息==========')
		msg += (f'\n调试模式：{gVar.is_debug}')
		msg += (f'\n心跳包显示：{gVar.is_show_heartbeat}')
		msg += (f'\n对接机器人：{gVar.self_name}({gVar.self_id})')
		msg += (f'\n管理员列表：{gVar.admin_id}')
		msg += (f'\n对接群列表：{gVar.rev_group}')
		reply(self.rev,msg)

	def QA_new(self):
		if re.search(r'(小|新|学|增加|添加|增添)(知识|问答|回答|对话)\s(\S+)=(\S+)', self.rev_msg):
			knowledge = re.search(r'(小|新|学|增加|添加|增添)(知识|问答|回答|对话)\s(\S+)=(\S+)', self.rev_msg).groups()
			key = knowledge[2]
			value = knowledge[3]
			query_key_pairs = {}
			query_key_pairs[key] = value
			QA_save(query_key_pairs)
			printf('记录新对话' + key + '：' + value)
			msg = QA_get('!!知识增加')
		else:
			msg = '请使用“新知识 提问关键字=回答”来记录问答'
		reply(self.rev,msg)

	def QA_reply(self):
		msg = QA_get(self.rev_msg)
		reply(self.rev,msg)

	def recall(self):
		if len(gVar.self_message):
			rev = gVar.self_message[-1]
			msg_id = rev['message_id']
			msg = rev['message']
			result = del_msg({'message_id':msg_id})
			gVar.self_message.pop()
			if status_ok(result):
				printf(f'撤回消息{LPURPLE}{msg}{RESET}成功！')
			else:
				msg = '撤回消息{LPURPLE}{msg}{RESET}出错'
				reply(self.rev,msg)
		else:
			msg = '暂无可撤回的历史消息'
			reply(self.rev,msg)

	def restart(self):
		msg = QA_get('!!重启')
		reply(self.rev,msg)
		gVar.is_running = False
		gVar.is_restart = True

	def say(self):
		if re.search(r'^向', self.rev_msg):
			inputs = re.search(r'([0-9]+)说\s?(\S*)', self.rev_msg).groups()
			number = inputs[0]
			send = inputs[1]
			result = False
			if re.search(r'向[0-9]+', self.rev_msg):
				result = status_ok(send_msg({'msg_type':'private','number':number,'msg':send}))
			else:
				result = status_ok(send_msg({'msg_type':'group','number':number,'msg':send}))
			if result: msg = f'发送消息“{send}”成功！'
			else: msg = f'发送消息失败！'
		else:
			msg = re.search(r'说\s?(\S*)', self.rev_msg).groups()[0]
		reply(self.rev,msg)

	def slience(self):
		if re.search(r'^开启', self.rev_msg):
			gVar.is_slience = True
		elif re.search(r'^关闭', self.rev_msg):
			gVar.is_slience = False
		else:
			gVar.is_slience = not gVar.is_slience
		write_config('Data','SlienceMode',gVar.is_slience)
		if gVar.is_slience:
			msg = '静默模式已开启'
		else:
			msg = '静默模式已关闭'
		warnf('静默模式已开启') if gVar.is_slience else warnf('静默模式已关闭')
		reply(self.rev,msg,True)

	def test(self):
		if re.search(r'^测试错误', self.rev_msg):
			raise RuntimeError('测试错误')
		else:
			thing = re.search(r'^测试(.*)', self.rev_msg).groups()[0]
			msg = f'测试{thing}OK!'
		reply(self.rev,msg)
		
	def unknow(self):
		msg = f'未知指令'
		reply(self.rev,msg)

	def voice(self):
		if re.search(r'语音\s?\S+', self.rev_msg):
			msg = '[CQ:tts,text=' + re.search(r'语音\s?(\S+)', self.rev_msg).groups()[0] + ' ]'
		else:
			msg = '[CQ:tts,text=请输入需要让我读出来的字嘛]'
		reply(self.rev,msg)