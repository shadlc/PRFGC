#!/usr/bin/python
#经过handle模块分类处理之后的操作函数

import time
import traceback

import global_variable as gVar
from print_color import *
from ifunction import *
from api_cqhttp import *
from module import *

class execute_msg(object):
  def __init__(self,rev,auth):
    try:
      for mod in gVar.modules:
        if mod(rev,auth).success:
          break
    except:
      if gVar.is_debug:
        reply(rev,f'{QA_get("!!致命错误")}{traceback.format_exc()}')
      else:
        reply(rev,f'{QA_get("!!致命错误")}{simplify_traceback(traceback.format_exc())}')
    
class execute_notice(object):
  def __init__(self,rev,auth):
    notice(rev,auth)
    
gVar.CMD = {'add': '对添加请求进行操作', 'cqhttp': '查看向CQHttp请求的历史记录', 'debug': '开关调试模式', 'deop': '取消管理员权限', 'device': '设置在线机型', 'exit': '关闭程序', 'get': '获取用户或群的信息', 'group': '修改对接群列表', 'groupmsg': '发送群聊消息', 'groupvoice': '发送群语音消息', 'help': '打开帮助菜单', 'history': '查看历史消息', 'info': '查看CQHttp版本和相关信息', 'msg': '发送私聊消息', 'notice': '发送群公告', 'ocr': '识别图片中的文字', 'op': '增加管理员权限', 'read': '读取转发消息内容', 'recall': '撤回消息', 'restart': '重启程序', 'reload': '重载配置文件', 'request': '手动调用CQHttpAPI', 'reply': '回复上一条消息(不支持快捷撤回)', 'say': '向主对接群发送消息', 'set': '设置变量', 'slience': '静默模式', 'stop': '关闭程序', 'test': '测试接口', 'voice': '发送语音消息'}
class execute_cmd(object):
  def __init__(self,cmd):
    self.cmd_list = {'添加': self.add, 'add': self.add, '历史请求': self.cqhttp, 'cqhttp': self.cqhttp, '调试': self.debug, 'debug': self.debug, '取消管理员': self.deop, 'deop': self.deop, '设备': self.device, 'device': self.device, 'exit': self.stop, '获取信息': self.get, 'get': self.get, '群': self.group, 'group': self.group, '群消息': self.groupmsg, 'groupmsg': self.groupmsg, '群语音': self.groupvoice, 'groupvoice': self.groupvoice, '帮助': self.help, '？': self.help, '?': self.help, 'help': self.help, '历史消息': self.history, 'history': self.history, '信息': self.info, 'info': self.info, 'msg': self.msg, '公告': self.notice, 'notice': self.notice, ' 识别': self.ocr, 'ocr': self.ocr, '管理员': self.op, 'op': self.op, 'read': self.read, '读取转发': self.read, '撤回': self.recall, 'recall': self.recall, '重启': self.restart, 'restart': self.restart, '重载': self.reload, 'reload': self.reload, '请求': self.request, 'request': self.request, '回复': self.reply, 'reply': self.reply, '说': self.say, 'say': self.say, '设置': self.set, 'set': self.set, '静默': self.slience, 'slience': self.slience, '关闭': self.stop, 'stop': self.stop, '测试': self.test, 'test': self.test, '语音': self.voice, 'voice': self.voice}
    if cmd != '':
      argv = cmd.split(' ',1)
      try:
        if len(argv)>1:
          self.cmd_list[argv[0]](argv[1])
        else:
          self.cmd_list[argv[0]]()
      except:
        warnf(f'未知指令！请使用help获取帮助')

  def add(self,argv=''):
    if re.search(r'(agree|deny)\s?(.*)',argv):
      inputs = re.search(r'(agree|deny)\s?(.*)',argv).groups()
      if not len(gVar.past_request):
        warnf('未寻找到上一条请求记录！')
      else:
        rev = gVar.past_request[-1]
        user_id = rev['user_id']
        user_name = get_user_name(user_id)
        if inputs[0] == 'agree':
          reply_add(rev,'true',inputs[1])
        else:
          reply_add(rev,'false',inputs[1])
    else:
      printf(f'请使用 {LCYAN}add agree/deny 备注{RESET} 同意或拒绝申请')

  def cqhttp(self,argv=''):
    printf(f'向CQHttp请求的历史记录：')
    for request in gVar.request_list:
      if re.search(r'^GET', request):
        printf(f'{LYELLOW}[GET]{RESET} {request.replace("GET","")}{LPURPLE}{RESET}')
      else:
        printf(f'{LYELLOW}[POST]{RESET} {request.replace("POST","")}{LPURPLE}{RESET}')

  def debug(self,argv=''):
    gVar.is_debug = not gVar.is_debug
    config_write('Data','DebugMode',gVar.is_debug)
    warnf('DEBUG模式已开启') if gVar.is_debug else warnf('DEBUG模式已关闭')

  def deop(self,argv=''):
    if re.search(r'(\d+)',argv):
      user_id = re.search(r'^(\d+)',argv).groups()[0]
      user_name = get_user_name(user_id)
      if user_id in gVar.admin_id:
        gVar.admin_id.remove(user_id)
        config_write('Data','Op',str(gVar.admin_id).strip('[\'\']').replace('\'',''))
        printf(f'{LPURPLE}{user_name}({user_id}){RESET}不再是管理员')
      else:
        warnf(f'{LPURPLE}{user_name}({user_id}){RESET}不是管理员！')
    else:
      printf(f'请使用 {LCYAN}deop 用户QQ{RESET} 取消管理员')

  def device(self,argv=''):
    if re.search(r'(.+)',argv):
      device = re.search(r'(.+)',argv).groups()[0]
      result = set_model_show({'model':device,'model_show':device})
      if status_ok(result):
        printf(f'成功设置新登陆设备为{LPURPLE}{device}{RESET}')
      else:
        printf(f'设置失败！')
    else:
      printf(f'请使用 {LCYAN}device 型号{RESET} 设置登陆设备型号')

  def get(self,argv=''):
    if re.search(r'user\s+(\d+)',argv):
      user_id = re.search(r'user\s+(\d+)',argv).groups()[0]
      result = get_stranger_info({'user_id':user_id})
      if status_ok(result):
        result = result['data']
        if result['sex'] == 'male': result['sex'] = '男'
        elif result['sex'] == 'female': result['sex'] = '女'
        else: result['sex'] = '其他'
        printf(f'用户{LPURPLE}{result["nickname"]}({user_id}){RESET}信息')
        printf(f'性别：{result["sex"]}')
        printf(f'年龄：{result["age"]}岁')
        printf(f'QQ等级：{result["level"]}级')
        printf(f'连续登陆时长：{result["login_days"]}天')
        printf(f'QQ身份卡：{result["qid"]}')
      else:
        printf(f'查无此账号！')
    elif re.search(r'group\s+(\d+)',argv):
      group_id = re.search(r'group\s+(\d+)',argv).groups()[0]
      result = get_group_info({'group_id':group_id})
      if status_ok(result):
        result = result['data']
        printf(f'群{LPURPLE}{result["group_name"]}({group_id}){RESET}信息')
        printf(f'群信息：{result["group_memo"]}')
        printf(f'群人数：{result["member_count"]}人')
        printf(f'群人数上限：{result["max_member_count"]}人')
        printf(f'群等级：{result["group_level"]}级')
      else:
        printf(f'查无此群！')
    else:
      printf(f'请使用 {LCYAN}get user/group QQ号/群号{RESET} 获取信息')

  def group(self,argv=''):
    if re.search(r'add\s+(\d+)',argv):
      group_id = re.search(r'\s+(\d+)',argv).groups()[0].strip()
      group_name = get_group_name(group_id)
      if group_id not in gVar.rev_group:
        gVar.rev_group.append(group_id)
        config_write('Data','ReceiveGroup',str(gVar.rev_group).strip('[]').replace('\'',''))
        printf(f'群{LPURPLE}{group_name}({group_id}){RESET}已添加至对接群列表')
      else:
        warnf(f'群{LPURPLE}{group_name}({group_id}){RESET}已经在对接群列表中！')
    elif re.search(r'remove\s+(\d+)',argv):
      group_id = re.search(r'\s+(\d+)',argv).groups()[0].strip()
      group_name = get_group_name(group_id)
      if group_id in gVar.rev_group:
        gVar.rev_group.remove(group_id)
        config_write('Data','ReceiveGroup',str(gVar.rev_group).strip('[]').replace('\'',''))
        printf(f'群{LPURPLE}{group_name}({group_id}){RESET}已从对接群列表中移除')
      else:
        warnf(f'群{LPURPLE}{group_name}({group_id}){RESET}不在对接群列表中！')
    elif re.search(r'main\s+(\d+)',argv):
      group_id = re.search(r'\s+(\d+)',argv).groups()[0].strip()
      group_name = get_group_name(group_id)
      if group_id in gVar.rev_group: gVar.rev_group.remove(group_id)
      gVar.rev_group.insert(0,group_id)
      config_write('Data','ReceiveGroup',str(gVar.rev_group).strip('[]').replace('\'',''))
      printf(f'群{LPURPLE}{group_name}({group_id}){RESET}已设置为主对接群')
    else:
      printf(f'请使用 {LCYAN}group add/remove 群号{RESET} 增加或删除对接群')
      printf(f'请使用 {LCYAN}group main 群号{RESET} 设置主对接群')

  def groupmsg(self,argv=''):
    if re.search(r'(\d+)\s+(.+)',argv):
      inputs = re.search(r'(\d+)\s+(.+)',argv).groups()
      group_id = inputs[0]
      group_name = get_group_name(group_id)
      msg = inputs[1]
      result = send_msg({'msg_type':'group','number':group_id,'msg':msg})
      if status_ok(result):
        printf(f'向群{LPURPLE}{group_name}({group_id}){RESET}发送消息：{LYELLOW}{msg}')
      else:
        warnf(f'向群{LPURPLE}{group_name}({group_id}){RESET}发送消息出错！请参考CQHttp端输出以及注意是否被禁言')
    else:
      printf(f'请使用 {LCYAN}groupmsg 群号 消息内容{RESET} 发送消息')

  def groupvoice(self,argv=''):
    if re.search(r'(\d+)\s+(.+)',argv):
      inputs = re.search(r'(\d+)\s+(.+)',argv).groups()
      group_id = inputs[0]
      group_name = get_group_name(group_id)
      msg = '[CQ:tts,text=' + inputs[1] + ' ]'
      result = send_msg({'msg_type':'group','number':group_id,'msg':msg})
      if status_ok(result):
        printf(f'向群{LPURPLE}{group_name}({group_id}){RESET}发送语音消息：{LYELLOW}{inputs[1]}')
      else:
        warnf(f'向群{LPURPLE}{group_name}({group_id}){RESET}发送语音消息出错！请参考CQHttp端输出')
    else:
      printf(f'请使用 {LCYAN}groupvoice 群号 语音消息{RESET} 发送消息')

  def help(self,argv=''):
    all_page = int(len(gVar.CMD) / 10 + 1)
    page = 1
    if re.search(r'(\d+)',argv): page = sorted([1,int(re.search(r'(\d+)',argv).groups()[0]), all_page])[1] 
    printf(f'============帮助============')
    for cmd in list(gVar.CMD.keys())[(page-1)*10:page*10]:
      printf(f'{LCYAN}{cmd}{RESET}：{gVar.CMD[cmd]}')
    printf(f'========第{page}页|共{all_page}页========')

  def history(self,argv=''):
    if re.search(r'(\d+)$',argv):
      msg_id = re.search(r'(\d+)$',argv).groups()[0]
      if ('g' + msg_id) in gVar.data:
        printf(f'群{LPURPLE}{get_group_name(str(msg_id))}({msg_id}){RESET}中的历史消息：')
        past_msg = get_group_msg_history({'group_id':msg_id})
        for i in range(len(past_msg)):
          msg_time = time.strftime("%m-%d %H:%M:%S", time.localtime(past_msg[i]['time']))
          msg_id = past_msg[i]['message_id']
          name = get_user_name(past_msg[i]['user_id'])
          msg = past_msg[i]['raw_message']
          printf(f'[{msg_time} {name}] {LPURPLE}(message_id:{msg_id}){RESET} {LYELLOW}{msg}{RESET}')
      elif ('u' + msg_id) in gVar.data:
        printf(f'与{LPURPLE}{get_user_name(msg_id)}{msg_id}{RESET}的历史消息：')
        past_msg = gVar.data['u' + msg_id].past_message
        for i in range(len(past_msg)):
          msg_time = time.strftime("%m-%d %H:%M:%S", time.localtime(past_msg[i]['time']))
          msg = past_msg[i]['raw_message']
          printf(f'[{msg_time}] {LYELLOW}{msg}{RESET}')
      else:
        printf(f'没有与{LPURPLE}{msg_id}{RESET}的消息记录')
    elif re.search(r'self',argv):
      if len(gVar.self_message):
        printf(f'自己发送的历史消息：')
        past_msg = gVar.self_message
        for i in range(len(past_msg)):
          msg_time = time.strftime("%m-%d %H:%M:%S", time.localtime(past_msg[i]['time']))
          msg = past_msg[i]['message']
          msg_id = past_msg[i]['message_id']
          printf(f'[{msg_time}] {LPURPLE}(message_id:{msg_id}){RESET} {LYELLOW}{msg}{RESET}')
      else:
        printf(f'没有自己发送的历史消息')
    else:
      printf(f'请使用 {LCYAN}history QQ号/群号/self{RESET} 获取历史消息')

  def info(self,argv=''):
    info = get_version_info()
    printf('=======CQHTTP版本信息=======')
    printf('内部应用名称：' + info['app_name'])
    printf('版本号：' + info['app_version'])
    printf('运行平台：' + info['runtime_os'])
    printf('登陆设备：' + info['device'])
    printf('==========变量信息==========')
    printf(f'调试模式：{LYELLOW}{gVar.is_debug}{RESET}')
    printf(f'静默模式：{LYELLOW}{gVar.is_slience}{RESET}')
    printf(f'心跳包显示：{LYELLOW}{gVar.is_show_heartbeat}{RESET}')
    printf(f'对接机器人：{LYELLOW}{gVar.self_name}({gVar.self_id}){RESET}')
    printf(f'管理员列表：{LYELLOW}{gVar.admin_id}{RESET}')
    printf(f'对接群列表：{LYELLOW}{gVar.rev_group}{RESET}')
    printf(f'显示全部群消息：{LYELLOW}{gVar.is_show_all_msg}{RESET}')
    printf(f'已安装模块：{LYELLOW}{gVar.modules_name}{RESET}')
    printf('=========字符画信息=========')
    printf(f'显示字符画：{LYELLOW}{gVar.is_show_image}{RESET}')
    printf(f'彩色字符画：{LYELLOW}{gVar.is_image_color}{RESET}')
    printf(f'字符画宽度范围：{LYELLOW}({gVar.min_image_width}:{gVar.max_image_width}){RESET}')
    printf('==========临时字典==========')
    printf(f'用户字典：{LYELLOW}{gVar.cache.user_name}{RESET}')
    printf(f'群字典：{LYELLOW}{gVar.cache.group_name}{RESET}')
    printf(f'数据字典：{LYELLOW}{list(gVar.data.keys())}{RESET}')
    printf('============================')

  def msg(self,argv=''):
    if re.search(r'(\d+)\s+(.+)',argv):
      inputs = re.search(r'(\d+)\s+(.+)',argv).groups()
      user_id = inputs[0]
      user_name = get_user_name(user_id)
      msg = inputs[1]
      result = send_msg({'msg_type':'private','number':user_id,'msg':msg})
      if status_ok(result):
        printf(f'向{LPURPLE}{user_name}({user_id}){RESET}发送消息：{msg}')
      else:
        warnf(f'向{LPURPLE}{user_name}({user_id}){RESET}发送消息出错！请参考CQHttp端输出')
    else:
      printf(f'请使用 {LCYAN}msg QQ号 消息内容{RESET} 发送消息')

  def notice(self,argv=''):
    if re.search(r'(\d+)\s+(.+)$',argv):
      inputs = re.search(r'(\d+)\s+(.+)$',argv).groups()
      group_id = inputs[0]
      group_name = get_group_name(group_id)
      notice = inputs[1]
      result = send_group_notice({'group_id':group_id,'content':notice})
      if status_ok(result):
        printf(f'向群{LPURPLE}{group_name}({group_id}){RESET}发布公告：{LYELLOW}{notice}')
      else:
        warnf(f'权限不足！向群{LPURPLE}{group_name}({group_id}){RESET}发布公告失败！')
    else:
      printf(f'请使用 {LCYAN}notice 群号 公告{RESET} 发布公告')

  def ocr(self,argv=''):
    if re.search(r'(\d+)',argv):
      img_id = re.search(r'(.+)',argv).groups()[0]
      result = ocr_image({'image':img_id})
      if status_ok(result):
        result = result['data']
        printf(f'图片{LPURPLE}({img_id}){RESET}识别结果')
        printf(f'文字语音：{result["language"]}')
        printf(f'-------------------------------------')
        for i in result['texts']:
          printf(f'文字内容：{i["text"]}')
          printf(f'结果置信度：{i["confidence"]}%')
          printf(f'-------------------------------------')
      else:
        printf(f'调用OCR失败！结果为：{result}')
    else:
      printf(f'未识别到文字！请使用 {LCYAN}ocr 图片ID{RESET} 识别图片内文字(图片ID即为[CQ:image,file=XXX]中的XXX)')

  def op(self,argv=''):
    if re.search(r'(\d+)',argv):
      user_id = re.search(r'(\d+)',argv).groups()[0]
      user_name = get_user_name(user_id)
      if user_id not in gVar.admin_id:
        gVar.admin_id.append(user_id)
        config_write('Data','Op',str(gVar.admin_id).strip('[]').replace('\'',''))
        printf(f'{LPURPLE}{user_name}({user_id}){RESET}已设置为管理员')
      else:
        warnf(f'{LPURPLE}{user_name}({user_id}){RESET}已经是管理员！')
    else:
      printf(f'请使用 {LCYAN}op 用户QQ{RESET} 设置管理员')

  def read(self,argv=''):
    if re.search(r'(.+)',argv):
      msg_id = re.search(r'(.+)',argv).groups()[0]
      msg_list = read_forward_msg(msg_id)
      if msg_list:
        group = 0
        for msg in msg_list:
          if group != msg['group_id']:
            group = msg['group_id']
            printf(f'{LPURPLE}{RESET}转发自群{LPURPLE}{get_group_name(str(group))}({group}){RESET}中的消息')
          msg_time = time.strftime("%m-%d %H:%M:%S", time.localtime(msg['time']))
          content = msg['content']
          name = msg['sender']['nickname']
          printf(f'[{msg_time} {LPURPLE}{name}{RESET}] {LPURPLE}{RESET} {LYELLOW}{content}{RESET}')
      else:
        printf(f'读取转发消息失败或仅支持读取群聊转发')
    else:
      printf(f'请使用 {LCYAN}read message_id{RESET} 读取转发消息')

  def recall(self,argv=''):
    if re.search(r'(.+)',argv):
      msg_id = re.search(r'(.+)',argv).groups()[0]
      result = del_msg({'message_id':msg_id})
      if status_ok(result):
        printf(f'撤回消息{LPURPLE}(message_id:{msg_id}){RESET}成功！')
      else:
        printf(f'撤回消息{LPURPLE}(message_id:{msg_id}){RESET}出错！')
    elif len(gVar.self_message):
      rev = gVar.self_message[-1]
      msg_id = rev['message_id']
      msg = rev['message']
      result = del_msg({'message_id':msg_id})
      if status_ok(result):
        gVar.self_message.pop()
        printf(f'撤回消息{LPURPLE}{msg}{RESET}成功！(使用 {LCYAN}history self{RESET} 查看其他历史消息)')
      else:
        printf(f'撤回消息{LPURPLE}{msg}{RESET}出错！(reply消息不支持快捷撤回)')
    else:
      warnf(f'未寻找到上一条可撤回的信息记录！请使用 {LCYAN}recall (消息ID){RESET} 快速撤回或撤回指定消息')

  def restart(self,argv=''):
    if argv == '':
      printf(f'正在重启程序...')
      gVar.is_running = False
      gVar.is_restart = True
    elif re.search(r'cqhttp',argv):
      set_restart()
      printf('CQHttp机器人已启动，正在连接CQHttp...', end='', console=False)
      connect_cqhttp()
      printf(f'正在监听来自{LPURPLE}{gVar.self_name}({gVar.self_id}){RESET}的消息')
    else:
      printf(f'请使用 {LCYAN}restart{RESET} 重启本程序')
      printf(f'请使用 {LCYAN}restart cqhttp{RESET} 重启CQHttp')

  def reload(self,argv=''):
    config_init()
    printf(f'重载配置文件成功！')

  def reply(self,argv=''):
    if gVar.latest_data not in gVar.data or len(gVar.data[gVar.latest_data].past_message) == 0:
      warnf('未寻找到上一条信息记录！')
    elif re.search(r'(.+)',argv):
      rev = gVar.data[gVar.latest_data].past_message[-1]
      msg = rev['raw_message']
      user_id = rev['user_id']
      user_name = get_user_name(user_id)
      reply_msg = re.search(r'(.+)',argv).groups()[0]
      result = quick_reply(rev,reply_msg)
      if status_ok(result):
        printf(f'上一消息为{LPURPLE}{user_name}({user_id}){RESET}发送的：{RESET}{LPURPLE}{msg}{RESET}')
        printf(f'回复：{LPURPLE}{reply_msg}{RESET}')
      else:
        printf(f'回复消息出错！请参考cqhttp端输出')
    else:
      printf(f'请使用 {LCYAN}reply 消息内容{RESET} 回复上一段信息')

  def request(self,argv=''):
    if re.search(r'(get|GET) (.+)',argv):
      url = re.search(r'(.+)',argv).groups()[0]
      result = get_request(url)
      if status_ok(result):
        printf(f'GET请求发送成功，返回为{LYELLOW}{result}{RESET}')
      else:
        warnf(f'GET发送请求出错，返回为{LYELLOW}{result}{RESET}')
    elif re.search(r'(post|POST) (.+) (.+)',argv):
      temp = re.search(r'(.+)',argv).groups()[0]
      url = temp[0]
      data = temp[1]
      result = post_request(url, data)
      if status_ok(result):
        printf(f'POST请求发送成功，返回为{LYELLOW}{result}{RESET}')
      else:
        warnf(f'POST发送请求出错，返回为{LYELLOW}{result}{RESET}')
    else:
      printf(f'请使用 {LCYAN}request [GET/POST] (POST请求体) 请求API{RESET} 向CQHttp发送请求(参考https://docs.go-cqhttp.org/api/)')

  def say(self,argv=''):
    if gVar.rev_group:
      if re.search(r'(.+)',argv):
        msg = re.search(r'(.+)',argv).groups()[0]
        group_name = get_group_name(gVar.rev_group[0])
        result = send_msg({'msg_type':'group','number':gVar.rev_group[0],'msg':msg})
        if status_ok(result):
          printf(f'向群{LPURPLE}{group_name}({gVar.rev_group[0]}){RESET}发送消息：{msg}')
        else:
          warnf(f'向群{LPURPLE}{group_name}({gVar.rev_group[0]}){RESET}发送消息出错！请参考cqhttp端输出以及注意是否被禁言')
      else:
        printf(f'请使用 {LCYAN}say 消息内容{RESET} 向主对接群发送消息')
    else:
      printf(f'请使用 {LCYAN}group main 群号{RESET} 设置主对接群')

  def set(self,argv=''):
    if re.search(r'self\s+(\S+)$',argv):
      if re.search(r'self\s+(\d+)$',argv):
        gVar.self_id = re.search(r'self\s(\d+)$',argv).groups()[0]
        gVar.self_name = get_user_name(gVar.self_id)
        gVar.at_info = '[CQ:at,qq=' + str(gVar.self_id) + ']'
        printf(f'设置机器人为{LPURPLE}{gVar.self_name}({gVar.self_id}){RESET}成功')
      elif re.search(r'self\s+auto$',argv):
        result = get_request('/get_login_info')
        gVar.self_name = result['data']['nickname']
        gVar.self_id = result['data']['user_id']
        gVar.at_info = '[CQ:at,qq=' + str(gVar.self_id) + ']'
        printf(f'自动设置机器人为{LPURPLE}{gVar.self_name}({gVar.self_id}){RESET}成功')
      else:
        printf(f'请使用 {LCYAN}set self QQ号/auto{RESET} 设置/自动设置机器人QQ')
    elif re.search(r'show',argv):
      if re.search(r'show\s+all',argv):
        gVar.is_show_all_msg = True
        config_write('Data','ShowAllMessage',gVar.is_show_all_msg)
        printf(f'设置显示所有群信息成功')
      elif re.search(r'show\s+at',argv):
        gVar.is_show_all_msg = False
        config_write('Data','ShowAllMessage',gVar.is_show_all_msg)
        printf(f'设置仅显示@群信息成功')
      else:
        printf(f'请使用 {LCYAN}set show all/at{RESET} 设置显示所有群信息或者是仅@群信息')
    elif re.search(r'heartbeat',argv):
      if re.search(r'(true|True)',argv): gVar.is_show_heartbeat = True
      elif re.search(r'(false|False)',argv): gVar.is_show_heartbeat = False
      else: gVar.is_show_heartbeat = not gVar.is_show_heartbeat
      config_write('Data','ShowHeartBeat',gVar.is_show_heartbeat)
      warnf('心跳包接收显示已开启') if gVar.is_show_heartbeat else warnf('心跳包接收显示已关闭')
    elif re.search(r'image\s+color',argv):
      if re.search(r'(true|True)',argv): gVar.is_image_color = True
      elif re.search(r'(false|False)',argv): gVar.is_image_color = False
      else: gVar.is_image_color = not gVar.is_image_color
      config_write('Data','ImageColor',gVar.is_image_color)
      printf('彩色字符画显示已开启') if gVar.is_image_color else printf('彩色字符画显示已关闭')
    elif re.search(r'image\s+minsize',argv):
      if re.search(r'minsize\s+(\d+)',argv):
        gVar.min_image_width = sorted([10,int(re.search(r'minsize\s+(\d+)',argv).groups()[0]),gVar.max_image_width])[1]
      config_write('Data','MinImageWidth',gVar.min_image_width)
      printf(f'图片字符画最小宽度已设置为{gVar.min_image_width}')
    elif re.search(r'image\s+maxsize',argv):
      if re.search(r'size\s+(\d+)',argv):
        gVar.max_image_width = sorted([gVar.min_image_width,int(re.search(r'size\s(\d+)',argv).groups()[0]),1000])[1]
      config_write('Data','MaxImageWidth',gVar.max_image_width)
      printf(f'图片字符画最大宽度已设置为{gVar.max_image_width}')
    elif re.search(r'image\s+size',argv):
      if re.search(r'(\d+)[^\d](\d+)',argv):
        size = re.search(r'(\d+)[^\d](\d+)',argv).groups()
        gVar.min_image_width = sorted([10,int(size[0]),int(size[1]),1000])[1]
        gVar.max_image_width = sorted([10,int(size[0]),int(size[1]),1000])[2]
      elif re.search(r'\s+(\d+)',argv):
        size = int(re.search(r'\s(\d+)',argv).groups()[0])
        gVar.min_image_width = sorted([10,size,1000])[1]
        gVar.max_image_width = gVar.min_image_width
      config_write('Data','MinImageWidth',gVar.min_image_width)
      config_write('Data','MaxImageWidth',gVar.max_image_width)
      printf(f'图片字符画大小已设置为({gVar.min_image_width}:{gVar.max_image_width})')
    elif re.search(r'image',argv):
      if re.search(r'(true|True)',argv): gVar.is_show_image = True
      elif re.search(r'(false|False)',argv): gVar.is_show_image = False
      else: gVar.is_show_image = not gVar.is_show_image
      config_write('Data','ShowImage',gVar.is_show_image)
      printf('图片字符画显示已开启') if gVar.is_show_image else printf('图片字符画显示已关闭')
    else:
      printf(f'==========设置列表==========')
      printf(f'{LCYAN}set self QQ号/auto{RESET} 设置机器人QQ号(用于辨别@信息)')
      printf(f'{LCYAN}set show all/at{RESET} 设置显示群信息类别')
      printf(f'{LCYAN}set image (true/false){RESET} 设置图片字符画显示')
      printf(f'{LCYAN}set image color (true/false){RESET} 设置彩色图片显示')
      printf(f'{LCYAN}set image minsize/maxsize 数字{RESET} 设置图片字符画最小/最大宽度')
      printf(f'{LCYAN}set image size 数字 数字{RESET} 设置图片字符画最小/最大宽度')
      printf(f'{LCYAN}set heartbeat (true/false){RESET} 设置心跳包是否接收')

  def slience(self,argv=''):
    gVar.is_slience = not gVar.is_slience
    config_write('Data','SlienceMode',gVar.is_slience)
    warnf('静默模式已开启') if gVar.is_slience else warnf('静默模式已关闭')

  def stop(self,argv=''):
    printf(f'正在关闭程序...')
    gVar.is_running = False
    gVar.is_restart = False

  def test(self,argv=''):
    msg = '测试OK！'
    printf(msg)

  def voice(self,argv=''):
    if re.search(r'(\d+)\s+(.+)',argv):
      inputs = re.search(r'(\d+)\s+(.+)',argv).groups()
      user_id = inputs[0]
      user_name = get_user_name(user_id)
      msg = '[CQ:tts,text=' + inputs[1] + ' ]'
      result = send_msg({'msg_type':'private','number':user_id,'msg':msg})
      if status_ok(result):
        printf(f'向{LPURPLE}{user_name}({user_id}){RESET}发送语音消息：{inputs[1]}')
      else:
        warnf(f'向{LPURPLE}{user_name}({user_id}){RESET}发送语音消息出错！请参考cqhttp端输出')
    else:
      printf(f'请使用 {LCYAN}voice QQ号 语音消息{RESET} 发送语音消息')

  def unknow(self,argv=''):
    warnf(f'未知指令！请输入 {LCYAN}help{RESET} 获取帮助！')
