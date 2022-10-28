#!/usr/bin/python
#作为函数库使用

from PIL import Image
import configparser
import requests
import random
import time
import io
import os
import re

from print_color import *
from api_cqhttp import *
import global_variable  as gVar

def module_enable(name,module):
	gVar.modules_name.append(name)
	gVar.modules.append(module)
	printf(f'{name}%DETECTED%',console=False)


def config_read(config):
	"""
	读取配置文件
	:param config: configparser对象
	"""
	gVar.cqhttp_url = config.get('CQHttp','CQHttpUrl')
	gVar.get_port = config.get('CQHttp','CQHttpPort')
	gVar.listening_port = config.get('CQHttp','ListeningPort')
	gVar.data_dir = config.get('CQHttp','DataDir')

	gVar.rev_group = config.get('Data','ReceiveGroup').split(', ') if 'ReceiveGroup' in config['Data'] else []
	gVar.admin_id = config.get('Data','Op').split(', ') if 'Op' in config['Data'] else []
	gVar.is_debug = True if 'True' == config.get('Data','DebugMode') else False
	gVar.is_slience = True if 'True' == config.get('Data','SlienceMode') else False
	gVar.is_show_heartbeat = True if 'True' == config.get('Data','ShowHeartBeat') else False
	gVar.is_show_all_msg = True if 'True' == config.get('Data','ShowAllMessage') else False
	gVar.is_show_image = True if 'True' == config.get('Data','ShowImage') else False
	gVar.is_image_color = True if 'ImageColor' in config['Data'] and 'True' == config.get('Data','ImageColor') else False
	gVar.min_image_width = int(config.get('Data','MinImageWidth')) if 'MinImageWidth' in config['Data'] else 10
	gVar.max_image_width = int(config.get('Data','MaxImageWidth')) if 'MaxImageWidth' in config['Data'] else 100

def config_write(section,option,value=None):
	"""
	写入配置文件
	:param section: 配置类型
	:param option: 配置名称
	:param value: 配置值
	"""
	config = configparser.ConfigParser()
	try:
		config.read(gVar.config_file)
		config.set(section,option,str(value))
		with open(gVar.config_file, mode='w') as f:
			config.write(f)
	except:
		errorf('写入配置文件失败！')

def config_reset(config):
	"""
	重置配置文件
	:param config: configparser对象
	"""
	print(gVar.first_start_info)
	with open(gVar.config_file, mode='w') as f:
		f.write('[CQHttp]\nCQHttpUrl = 127.0.0.1\nCQHttpPort = 5700\nListeningPort = 5701\nDataDir = ../cqhttp/data\n\n[Data]\nDebugMode = False\nSlienceMode = False\nShowHeartBeat = False\nShowAllMessage = False\nShowImage = False')

def config_init():
	"""
	初始化配置文件
	"""
	config = configparser.ConfigParser()
	try:
		config.read(gVar.config_file)
		config_read(config)
	except:
		config_reset(config)
		config.read(gVar.config_file)
		config_read(config)

def import_json(file):
	if not os.path.exists(file):
		try:
			open(file,'w', encoding='utf-8').write("{}")
		except:
			errorf('导入配置文件失败！')
			return None
	return json.load(open(file, 'r', encoding='utf-8'))

def save_json(file_name, data):
	try:
		json.dump(data,open(file_name, 'w',encoding='utf-8'),indent=2,ensure_ascii=False)
	except:
		errorf('写入数据失败！')
  

def calc_size(bytes):
	"""
	格式化文件大小
	:param bytes: 字节数
	:return: 格式化文件大小
	"""
	symbols = ('KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
	prefix = dict()
	for a, s in enumerate(symbols):
		prefix[s] = 1 << (a + 1) * 10
	for s in reversed(symbols):
		if int(bytes) >= prefix[s]:
			value = float(bytes) / prefix[s]
			return '%.2f%s' % (value, s)
	return ".%sB" % bytes

def char_add_color(char,rgb):
	"""
	为字符添加颜色代码
	:param char: 字符
	:param rgb: 颜色rgb代码
	:return: 添加了颜色代码的字符
	"""
	R = rgb[0]
	G = rgb[1]
	B = rgb[2]
	if R<=100 and G<=100 and B<=100:
		return char
	elif R>=G and R>=B:
		if R-G<=50 and R-B<=50: return char
		elif B>=G and R<B<<1: return LPURPLE + char + RESET
		elif G>=B and R<G<<1: return LYELLOW + char + RESET
		else: return LRED + char + RESET
	elif G>=R and G>=B:
		if G-R<=50 and G-B<=50: return char
		elif B>=R and G<B<<1: return LCYAN + char + RESET
		elif R>=B and G<G<<1: return LYELLOW + char + RESET
		else: return LGREEN + char + RESET
	elif B>=R and B>=G:
		if B-G<=50 and B-R<=50: return char
		elif R>=G and B<R<<1: return PURPLE + char + RESET
		elif G>=R and B<G<<1: return LBLUE + char + RESET
		else: return BLUE + char + RESET
	else: return char

def msg_img2char(msg):
	"""
	检测CQ码中有图片并转化为字符画
	:param msg: 收到的消息
	:param color: 是否渲染颜色
	:return: 转化为字符画的消息
	"""
	while re.search(r'\[CQ:image.*?\]',msg) and '的消息' in msg:
		image_ascii =  list(".:~+o0O*#%@")
		unit = (256+1)/len(image_ascii)
		url = re.search(r'\.image,url=(.*)]',msg).groups()[0]
		img = Image.open(io.BytesIO(requests.get(url).content)).convert('RGB')
		w,h = img.size
		ratio = h/float(w)
		tartget_w = sorted([gVar.min_image_width,w,gVar.max_image_width])[1]
		tartget_h = int(tartget_w * ratio * 0.5)
		img = img.resize((tartget_w,tartget_h))
		pixels = img.getdata()
		char = ''
		row = 0
		for i in pixels:
			pixel_gray = (i[0]*38 + i[1]*75 + i[2]*15) >> 7
			single_char = image_ascii[int(pixel_gray//unit)]
			if gVar.is_image_color: char += char_add_color(single_char,i)
			else: char += single_char
			row += 1
			if row >= tartget_w:
				row = 0
				char += '\n'
		msg = msg.replace(re.search(r'(\[CQ:image.*?\])',msg).groups()[0],'\n'+ char)
	return msg

def status_ok(respond):
	"""
	检测cqhttp接口是否返回正常
	:param respond: cqhttp返回的json信息
	:return: 此接口是否正常执行
	"""
	if 'status' in respond and respond['status'] == 'ok':
		return True
	else:
		return False

def handle_placehold(text,placehold_dict):
	pattern = re.compile(r'(%\S+?%)')
	flags = pattern.findall(str(text))
	for flag in flags:
		if flag.replace('%','') in placehold_dict:
			text = re.sub(flag, placehold_dict[flag.replace('%','')], str(text))
	return text

def reply(rev,msg,force=False):
	"""
	快捷回复消息
	:param rev: 接收到的消息json信息
	:param msg: 发送的消息内容
	:param force: 无视静默模式发送消息
	:return: 发送消息后返回的json信息
	"""
	msg = handle_placehold(str(msg),gVar.placehold_dict)
	if rev['post_type'] == 'message' and(not gVar.is_slience or force):
		if rev['message_type'] == 'group':
			group_id = rev['group_id']
			group_name = get_group_name(group_id)
			printf(f'{LGREEN}[SEND]{RESET}向群{LPURPLE}{group_name}({group_id}){RESET}发送消息：{msg}')
			return send_msg({'msg_type':'group','number':group_id,'msg':msg})
		else:
			user_id = rev['user_id']
			user_name = get_user_name(user_id)
			printf(f'{LGREEN}[SEND]{RESET}向{LPURPLE}{user_name}({user_id}){RESET}发送消息：{msg}')
			return send_msg({'msg_type':'private','number':user_id,'msg':msg})

def reply_id(type,id,msg,force=False):
	"""
	按id回复消息
	:param type: 发送类型
	:param id: 发送的对象id
	:param msg: 发送的消息内容
	:return: 发送消息后返回的json信息
	"""
	msg = handle_placehold(str(msg),gVar.placehold_dict)
	if (not gVar.is_slience or force):
		if type == 'group':
			printf(f'{LGREEN}[SEND]{RESET}向群{LPURPLE}{get_group_name(id)}({id}){RESET}发送消息：{msg}')
			return send_msg({'msg_type':'group','number':id,'msg':msg})
		else:
			printf(f'{LGREEN}[SEND]{RESET}向{LPURPLE}{get_user_name(id)}({id}){RESET}发送消息：{msg}')
			return send_msg({'msg_type':'private','number':id,'msg':msg})

def reply_back(owner_id, msg):
  if owner_id[:1] == 'u':
    reply_id('private',owner_id[1:], msg)
  else:
    reply_id('group',owner_id[1:], msg)

def quick_reply(rev,msg):
	"""
	调用“.handle_quick_operation”接口的快捷回复消息
	:param rev: 接收到的消息json信息
	:param msg: 发送的消息内容
	:return: 发送消息后返回的json信息
	"""
	msg = handle_placehold(str(msg),gVar.placehold_dict)
	if rev['post_type'] == 'message':
		gVar.self_message.append({'message':msg,'message_id':0,'message_type':rev['message_type'],'user_id':gVar.self_id,'time':time.time()})
		return handle_quick_operation({'context':rev,'operation':{'reply':msg}})

def reply_add(rev,accept,msg):
	"""
	回复添加请求
	:param rev: 接收到的请求json信息
	:param accept: 是否接受
	:param msg: 操作理由
	:return: 发送消息后返回的json信息
	"""
	if rev['post_type'] == 'request':
		return handle_quick_operation({'context':rev,'operation':{'approve':accept,'remark':msg,'reason':msg}})

def get_user_name(id):
	"""
	获取用户信息
	:param id: 用户的qq号
	:return: 用户信息
	"""
	id = str(id)
	if id in gVar.cache.user_name:
		return gVar.cache.user_name[id]
	else:
		result = get_stranger_info({'user_id':id})
		if 'status' in result and result['status'] == 'ok':
			name = result['data']['nickname']
			gVar.cache.user_name[id] = name
			return name
		else:
			return ''

def get_group_name(id):
	"""
	获取群信息
	:param id: 群号
	:return: 群信息
	"""
	id = str(id)
	if id in gVar.cache.group_name:
		return gVar.cache.group_name[id]
	else:
		result = get_group_info({'group_id':id})
		if 'status' in result and result['status'] == 'ok':
			name = result['data']['group_name']
			gVar.cache.group_name[id] = name
			return name
		else:
			return ''

def get_image_url(file):
	"""
	获取图片下载URL
	:param file: 文件的标识码
	:return: 文件下载链接
	"""
	if 'status' in respond and respond['status'] == 'ok':
		return get_image({'file':file})
	else:
		return False

def QA_fetch():
	"""
	读取QA文件
	:return: 字典形式的QA数据
	"""
	query_key_pairs = {}
	with open(gVar.QA_file, 'r', encoding='utf-8-sig') as f:
		# each line like Q: query A: answer
		for line in f:
			if line.strip() == '': continue
			left, right = line.split('A:')
			query = left.strip().replace('Q:','')
			answer = right.strip().replace('\\n','\n')
			if query in query_key_pairs.keys():
				query_key_pairs[query].append(answer)
			else:
				query_key_pairs[query] = [answer]
	return query_key_pairs

def QA_save(query_key_pairs):
	"""
	保存QA组合
	:param query_key_pairs: QA字典格式数据
	"""
	with open(gVar.QA_file, 'a', encoding='utf-8-sig') as f:
		for key in query_key_pairs:
			f.write(f'Q:{key}	A:{query_key_pairs[key]}\n')

def QA_contains(msg):
	"""
	检测QA数据中是否存在
	:param msg: 需要检测的键值
	:return: 是否存在
	"""
	for name in QA_fetch().keys():
		if '#' in name and msg == name[1:]:
			return True
		if name in msg:
			return True
	return False

def QA_get(msg):
	"""
	获取QA的对应数据
	:param msg: 需要搜寻的键值
	:return: 键值的对应数据
	"""
	max_match = 1
	answer_list = []
	for query,answers in QA_fetch().items():
		match = len(set(query) & set(str(msg)))
		if match >= max_match:
			max_match = match
			answer_list = answers
	return random.choice(answer_list)

def printf(msg,end='\n',console=True):
	"""
	向控制台输出通知级别的消息
	:param msg: 信息
	:param end: 末尾字符
	:param console: 是否增加一行<console>
	"""
	msg = handle_placehold(str(msg),gVar.placehold_dict)
	prefix = '\r[' + time.strftime("%H:%M:%S", time.localtime()) + ' INFO] '
	if gVar.is_show_image: msg = msg_img2char(msg)
	print(f'{prefix}{msg}',end=end)
	if console:print(f'\r{LGREEN}<console>{RESET} ',end='')

def warnf(msg,end='\n',console=True):
	"""
	向控制台输出警告级别的消息
	:param msg: 信息
	:param end: 末尾字符
	:param console: 是否增加一行<console>
	"""
	msg = handle_placehold(str(msg),gVar.placehold_dict)
	msg = msg.replace(RESET,LYELLOW)
	prefix = '\r[' + time.strftime("%H:%M:%S", time.localtime()) + ' WARN] '
	print(f'{LYELLOW}{prefix}{msg}{RESET}',end=end)
	if console: print(f'\r{LGREEN}<console>{RESET} ',end='')

def errorf(msg,end='\n',console=True):
	"""
	向控制台输出错误级别的消息
	:param msg: 信息
	:param end: 末尾字符
	:param console: 是否增加一行<console>
	"""
	msg = handle_placehold(str(msg),gVar.placehold_dict)
	prefix = '\r[' + time.strftime("%H:%M:%S", time.localtime()) + ' ERROR] '
	print(f'{LRED}{prefix}{msg}{RESET}',end=end)
	if console: print(f'\r{LGREEN}<console>{RESET} ',end='')

def simplify_traceback(tb):
	"""
	获取错误报告并简化
	:param tb: 获取的错误报告
	:return: 易读的错误报告
	"""
	result = '按从执行顺序排序有\n'
	tb = tb.strip().split('\n')
	for excepts in tb[1:]:
		if re.search(r'(\\|/)(\w*?\.py).*line\s([0-9]+).*in\s(.*)', excepts):
			temp = re.search(r'(\\|/)(\w*?\.py).*line\s([0-9]+).*in\s(.*)', excepts).groups()
			result += f'文件{temp[1]}中第{temp[2]}行的“{temp[3]}”方法出错\n'
	result += f'导致最终错误为“{tb[-1]}”'
	return result