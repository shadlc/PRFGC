#!/usr/bin/python
#CQHTTP API文件

import requests
import socket
import json
import time

import global_variable as gVar

def request_to_json(msg):
	for i in range(len(msg)):
		if msg[i]=='{':
			return json.loads(msg[i:])

def get_request(url):
	try:
		get_url = 'http://' + gVar.cqhttp_url + ':' + gVar.get_port + url
		gVar.latest_request = get_url
		r = requests.get(get_url)
		rev_json = json.loads(r.text)
		return rev_json
	except:
		return {}

def connect_cqhttp():
	connected = False
	while not connected:
		print(".", end = '', flush = True)
		result = get_request('/get_status')
		connected = True if 'data' in result and result['data']['online'] else False
		time.sleep(1)
	print(f'CQHttp已连接！')
	result = get_request('/get_login_info')
	gVar.self_name = result['data']['nickname']
	gVar.self_id = result['data']['user_id']
	gVar.at_info = '[CQ:at,qq=' + str(gVar.self_id) + '] '
	return [result['data']['nickname'],result['data']['user_id']]

def receive_msg():
	server = socket.socket()
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server.bind((gVar.cqhttp_url, int(gVar.listening_port)))
	server.listen(100)
	header = 'HTTP/1.1 200 OK\n\n'
	client, address = server.accept()
	request = client.recv(32767).decode(encoding='utf-8')
	client.sendall(header.encode(encoding='utf-8'))
	rev_json = request_to_json(request)
	server.close()
	return rev_json

def send_msg(resp_dict):
	msg_type = resp_dict['msg_type']  # 回复类型（群聊/私聊）
	number = resp_dict['number']  # 回复账号（群号/好友号）
	msg = str(resp_dict['msg'])  # 要回复的消息
	# 将字符中的特殊字符进行url编码
	msg = msg.replace(' ', '%20')
	msg = msg.replace('\n', '%0a')
	msg = msg.replace('[', '%5b')
	msg = msg.replace(']', '%5d')
	msg = msg.replace('&', '%26')
	msg = msg.replace('#', '%23')
	msg = msg.replace(';', '%3b')
	msg = msg.replace('\'', '%22')
	msg = msg.replace('\\', '%5c')
	if msg_type == 'group':
		url = '/send_group_msg?group_id=' + str(number) + '&message=' + msg
	elif msg_type == 'private':
		url = '/send_private_msg?user_id=' + str(number) + '&message=' + msg
	result = get_request(url)
	if 'status' in result and result['status'] == 'ok':
		gVar.self_message.append(get_msg({'message_id':result['data']['message_id']})['data'])
	return result

def del_msg(resp_dict):
	message_id = resp_dict['message_id']  # 消息ID
	url = '/delete_msg?message_id=' + str(message_id)
	return get_request(url)

def get_msg(resp_dict):
	message_id = resp_dict['message_id']  # 消息ID
	url = '/get_msg?message_id=' + str(message_id)
	return get_request(url)

def send_group_notice(resp_dict):
	group_id = resp_dict['group_id']  # 群号
	content = resp_dict['content']  # 公告内容
	url = '/_send_group_notice?group_id=' + str(group_id) + '&content' + content
	return get_request(url)

def get_image(resp_dict):
	file = resp_dict['file']  # 图片缓存文件名
	url = '/get_image?file=' + str(file)
	return get_request(url)

def handle_quick_operation(resp_dict):
	context = resp_dict['context']  # 事件数据对象
	operation = resp_dict['operation']  # 快速操作对象
	url = '/.handle_quick_operation?context=' + str(json.dumps(context)) + '&operation=' + str(json.dumps(operation))
	return get_request(url)

def ocr_image(resp_dict):
	image = resp_dict['image']  # 图片ID
	url = '/.ocr_image?image=' + image
	return get_request(url)

def upload_group_file(resp_dict):
	group_id = resp_dict['group_id']  # 群号
	file = resp_dict['file']  # 文件目录
	name = resp_dict['name']  # 文件名称
	url = '/upload_group_file?group_id=' + str(group_id) + '&file=' + file + '&name=' + name
	return get_request(url)

def get_group_msg_history(resp_dict):
	group_id = resp_dict['group_id']  # 群号
	if 'message_seq' in resp_dict:
		message_seq = resp_dict['message_seq']
		url = '/get_group_msg_history?group_id=' + str(group_id) + '&message_seq=' + str(message_seq)
	else:
		url = '/get_group_msg_history?group_id=' + str(group_id)
	return get_request(url)

def get_stranger_info(resp_dict):
	user_id = resp_dict['user_id']  # 目标QQ号
	url = '/get_stranger_info?user_id=' + str(user_id)
	return get_request(url)

def get_group_info(resp_dict):
	group_id = resp_dict['group_id']  # 目标群号
	url = '/get_group_info?group_id=' + str(group_id)
	return get_request(url)

def get_model_show(resp_dict):
	model = resp_dict['model']  # 机型
	url = '/_set_model_show?model=' + model
	return get_request(url)

def set_model_show(resp_dict):
	model = resp_dict['model']  # 机型
	model_show = resp_dict['model_show']  # 机型后缀
	url = '/_set_model_show?model=' + model + '&model_show=' + model_show
	return get_request(url)

def get_version_info():
	result = get_request('/get_version_info')
	if 'status' in result and result['status'] == 'ok':
		device = ''
		if 0 == result['data']['protocol']: device = 'iPad'
		elif 1 == result['data']['protocol']: device = '安卓设备'
		elif 2 == result['data']['protocol']: device = '安卓手表'
		elif 3 == result['data']['protocol']: device = 'MacOS'
		elif 4 == result['data']['protocol']: device = '企点设备'
		else: device = '未知设备'
		return {'app_name':result['data']['app_name'],'app_version':result['data']['app_version'],'runtime_os':result['data']['runtime_os'],'device':device}
	else:
		return ''

def set_restart():
	url = '/set_restart'
	return get_request(url)