#!/usr/bin/python
#处理信息接口

import threading
import re

import global_variable as gVar
from print_color import *
from ifunction import *
from execute import *

#消息处理接口主函数
def handle_msg(rev):

	#定义全局变量
	global data,msg_id,rev_msg,group_id,group_name,user_id,user_name,post_type,post_time,msg_type,notice_type,sub_type,font,target_id,target_name,operator_id,operator_name

	#上报类型 message消息 notice系统提示 request请求
	post_type = rev['post_type'] if 'post_type' in rev else ''
	#事件发生的时间戳
	post_time = rev['time'] if 'time' in rev else ''
	#消息类型 private私聊 group群聊
	msg_type = rev['message_type'] if 'message_type' in rev else ''
	#通知类型 notify常用通知 essence群精华消息 group_upload群文件上传 group_admin群变动 group_decrease群成员减少 group_increase群成员增加 group_ban群禁言 friend_add好友添加 group_recall群消息撤回 friend_recall好友消息撤回 group_card群成员名片更新 offline_file离线文件 client_status客户端状态变更
	notice_type = rev['notice_type'] if 'notice_type' in rev else ''
	#消息子类型 friend好友 group群临时会话 group_self群聊 other其他 normal普通 anonymous匿名 notice系统提示
	sub_type = rev['sub_type'] if 'sub_type' in rev else ''
	#消息 ID
	msg_id = rev['message_id'] if 'message_id' in rev else ''
	#原始消息内容
	rev_msg = rev['message'] if 'message' in rev else ''
	#发送者QQ号
	user_id = str(rev['user_id']) if 'user_id' in rev else ''
	#发送者昵称
	user_name = get_user_name(user_id) if user_id else ''
	#群号
	group_id = str(rev['group_id']) if 'group_id' in rev else ''
	#群名
	group_name = get_group_name(group_id) if group_id else ''
	#目标QQ号
	target_id = str(rev['target_id']) if 'target_id' in rev else ''
	#目标昵称
	target_name = get_user_name(target_id) if target_id else ''
	#操作者QQ号
	operator_id = str(rev['operator_id']) if 'operator_id' in rev else ''
	#操作者昵称
	operator_name = get_user_name(operator_id) if operator_id else ''

	#如果是调试模式，输出所有接收到的原始信息
	if gVar.is_debug and not post_type == 'meta_event':
		printf(f'{LYELLOW}[DATA]{RESET}接收到CQHTTP数据包{LYELLOW}{rev}{RESET}')

	#选择存储的数据
	if user_id == gVar.self_id:
		pass
	elif group_id:
		if ('g' + str(group_id)) not in gVar.data:
			gVar.data['g' + str(group_id)] = gVar.memory()
		data = gVar.data['g' + str(group_id)]
		gVar.latest_data = 'g' + str(group_id)
	elif user_id:
		if ('u' + str(user_id)) not in gVar.data:
			gVar.data['u' + str(user_id)] = gVar.memory()
		data = gVar.data['u' + str(user_id)]
		gVar.latest_data = 'u' + str(user_id)


	#预处理消息（图片消息链接处理）
	if 'message' in rev:
		rev['message'] = re.sub(r',url=.*]',']',rev['message'])

	#分类处理消息
	if user_id == gVar.self_id:
		pass
	elif post_type == 'message':
		if group_id:
			gVar.data['g' + str(group_id)].past_message.append(rev)
		else:
			gVar.data['u' + str(user_id)].past_message.append(rev)
		if str(user_id) in gVar.admin_id:
			return message(rev,1)
		elif group_id:
			if group_id in gVar.rev_group:
				return message(rev,2)
			else:
				return message(rev)
		else:	
			if sub_type == 'friend':
				return message(rev,2)
			else:
				return message(rev)
	elif post_type == 'notice':
		if group_id: gVar.data['g' + str(group_id)].past_notice.append(rev)
		else: gVar.data['u' + str(user_id)].past_notice.append(rev)
		return notice(rev)
	elif post_type == 'request':
		return request(rev)
	else:
		return event(rev)

#终端命令处理
def handle_console(rev):
	return execute_cmd(rev)

#消息处理
def message(rev, auth=3):
	if not group_id:
		printf(f'{LBLUE}[RECEIVE]{RESET}收到来自{LPURPLE}{user_name}({user_id}){RESET}的消息：{rev_msg}')
	elif group_id:
		if gVar.at_info in rev_msg:
			printf(f'{LBLUE}[RECEIVE]{RESET}收到群{LPURPLE}{group_name}({group_id}){RESET}内{LPURPLE}{user_name}({user_id}){RESET}的消息：{rev_msg}')
		elif gVar.is_show_all_msg:
			printf(f'{LBLUE}[RECEIVE]{RESET}收到群{LPURPLE}{group_name}({group_id}){RESET}内{LPURPLE}{user_name}({user_id}){RESET}的消息：{rev_msg}')

	thread = threading.Thread(target=execute_msg, args=[rev,auth])
	thread.setDaemon(True)
	thread.start()

def notice(rev, auth=3):

	thread = threading.Thread(target=execute_notice, args=[rev,auth])
	thread.setDaemon(True)
	thread.start()

def request(rev, auth=3):
	request_type = rev['request_type']
	comment = rev['comment']
	if request_type == 'friend':
		printf(f'{LYELLOW}[NOTICE]{RESET}{LPURPLE}{user_name}({user_id}){RESET}发送好友请求{LPURPLE}{comment}{RESET}，使用 {LCYAN}add agree/deny 备注{RESET} 同意或拒绝此请求')
	elif request_type == 'group':
		printf(f'{LYELLOW}[NOTICE]{RESET}{LPURPLE}{user_name}({user_id}){RESET}发送加群请求{LPURPLE}{comment}{RESET}，使用 {LCYAN}add agree/deny 理由{RESET} 同意或拒绝此请求')

def event(rev, auth=3):
	if gVar.is_show_heartbeat:
		received = rev['status']['stat']['PacketReceived']
		printf(f'{LYELLOW}[NOTICE]{RESET}接收到CQHTTP的第{LPURPLE}{received}{RESET}个心跳包')