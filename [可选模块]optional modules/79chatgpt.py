#!/usr/bin/python
#ChatGPT模块处理
# 该模块需要后端配合方可使用


import global_variable as gVar
from ifunction import *
from api_cqhttp import *

import json
import time
import html

module_name = "ChatGPT模块"
data_file = 'data/chatgpt_data.json'
config = import_json(data_file)

class chatgpt:
  def __init__(self,rev,auth):
    self.success = True
    self.rev = rev
    self.post_type = self.rev["post_type"] if "post_type" in self.rev else ""
    self.post_time = self.rev["time"] if "time" in self.rev else ""
    self.msg_type = self.rev["message_type"] if "message_type" in self.rev else ""
    self.notice_type = self.rev["notice_type"] if "notice_type" in self.rev else ""
    self.sub_type = self.rev["sub_type"] if "sub_type" in self.rev else ""
    self.msg_id = self.rev["message_id"] if "message_id" in self.rev else ""
    self.rev_msg = self.rev["message"] if "message" in self.rev else ""
    self.user_id = self.rev["user_id"] if "user_id" in self.rev else 0
    self.user_name = get_user_name(str(self.user_id)) if self.user_id else ""
    self.group_id = self.rev["group_id"] if "group_id" in self.rev else 0
    self.group_name = get_group_name(str(self.group_id)) if self.group_id else ""
    self.target_id = self.rev["target_id"] if "target_id" in self.rev else 0
    self.target_name = get_user_name(str(self.target_id)) if self.target_id else ""
    self.operator_id = self.rev["operator_id"] if "operator_id" in self.rev else 0
    self.operator_name = get_user_name(str(self.operator_id)) if self.operator_id else ""

    #初始化此模块需要的数据
    if self.group_id:
      self.owner_id = f"g{self.group_id}"
    else:
      self.owner_id = f"u{self.user_id}"
    self.data = gVar.data[self.owner_id]
    
    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if False: self.chatgpt_help(auth)
      elif auth<=3 and re.search(r'^重置(会话|对话|聊天)$',self.rev_msg): self.reset_conv(auth)
      # elif auth<=3 and re.search(r'^gpt4 ',self.rev_msg): self.gpt4()
      elif auth<=3 and re.search(r'^bing ',self.rev_msg): self.edgegpt()
      elif auth<=3: self.chatgpt()
      else: self.success = False

    # #检测开头"gpt4"触发
    # elif re.search(r'^gpt4 ',self.rev_msg):
    #   if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,"").strip()
    #   self.gpt4()

    #检测开头"bing"触发
    elif re.search(r'^bing ',self.rev_msg):
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,"").strip()
      self.edgegpt()

    #检测开头#号触发
    elif re.search(r"^#\S+", self.rev_msg):
      self.rev_msg = self.rev_msg[1:]
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,"").strip()
      if auth<=3: self.chatgpt()
      else: self.success = False
    else: self.success = False

  def chatgpt_help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=3:
      msg += '\n直接@我发送消息就能和我聊天啦~'
      msg += '\n重置会话 |重置当前会话记忆'
      msg += '\n发送“bing 问题”可以让让我化身New Bing和你聊天~'
      #msg += '\n发送“gpt4 问题”可以让让我更机智的和你和你聊天~'
    reply(self.rev,msg)

  def chatgpt(self):
    text = text_preprocess(self.rev_msg)
    msg = get_chatgpt(text, self.user_name, self.owner_id)
    if re.search(r"\[paint_prompt:.+\]", msg):
      prompt = re.search(r"(\[paint_prompt:.+\])", msg).groups()[0]
      printf(f'{LYELLOW}[{module_name}]{RESET} 向StableDiffusion获取画作: {prompt}')
      gen_json = config["webui_default_json"].copy()
      gen_json["prompt"] += prompt
      msg = re.sub(r"(\[paint_prompt:.+\])", "", msg)
      reply(self.rev, self.reply_code() + msg)
      image = get_stable_diffusion(gen_json)
      reply(self.rev, image)
    elif msg:
      reply(self.rev, self.reply_code() + msg)

  def gpt4(self):
    text = text_preprocess(self.rev_msg[5:])
    msg = get_gpt4(text, self.user_name, self.owner_id)
    reply(self.rev, self.reply_code() + msg)

  def edgegpt(self):
    text = text_preprocess(self.rev_msg[5:])

    if re.search(r"^重置(会话|对话|聊天)$", text):
      msg = reset_edgegpt_conv(f"{gVar.self_id}{self.owner_id}")
    else:
      request_times = 0
      while not edgegpt_avalible():
        if request_times == 0:
          reply(self.rev, self.reply_code() + "[New Bing] 有正在处理的对话，正在排队等候响应(60秒超时)...")
        if request_times >= 30:
          reply(self.rev, self.reply_code() + "[New Bing] 调用超时，请重试...")
          return
        request_times += 1
        time.sleep(2)
      reply(self.rev, self.reply_code() + "[New Bing] 正在处理中...")
      msg = get_edgegpt(text, self.user_name, self.owner_id)
    reply(self.rev, self.reply_code() + msg)

  def reset_conv(self, auth):
    if not self.group_id or auth <= 2:
      if reset_chatgpt_conv(f"{gVar.self_id}{self.owner_id}"):
        msg = "[ChatGPT] 此会话记忆已清除"
      else:
        msg = "[ChatGPT] 重置会话出错！"
    else:
      msg = "您无权限这样做！"
    reply(self.rev, msg)

  def reply_code(self):
    if len(str(self.msg_id)) > 6:
      msg = f"[CQ:reply,id={self.msg_id}]"
    else:
      msg = ""
    return msg



def text_preprocess(text):
    text = re.sub(r'\[CQ:(json|xml|forward|reply),.*\]', '', text)
    if re.search(r'\[CQ:image,file=(.*),url', text):
      image_file = re.search(r'\[CQ:image,file=(.*),url', text).groups()[0]
      result = ocr_image({'image': image_file})
      if gVar.is_debug: printf(f'{result}')
      if status_ok(result):
        discribe = ''.join([x["text"] for x in result["data"]["texts"] if x["confidence"] >= 80])
        text = re.sub(r'\[CQ:image.*\]', f'[图片|内容描述:{discribe}]', text)
        printf(f'[{module_name}] 解析图片内容:{discribe}')
      else:
        text = re.sub(r'\[CQ:image.*\]', '[图片]', text)
    elif re.search(r'\[CQ:record,.*url=(.*)\]', text):
      text = re.sub(r'\[CQ:record.*\]', '[语言]', text)
    return text

def get_chatgpt(text, user_name=None, chat_id="temp"):
  post_json = {
    "message": f"({user_name}对你说){text}",
    "user": str(user_name),
    "bot_id": str(gVar.self_id),
    "chat_id": str(chat_id)
  }
  if gVar.is_debug: printf(f"调用 ChatGPT API (/chat)：{post_json}")
  dat = json.dumps(post_json)
  response = ""
  try:
    response = requests.post(config["chatgpt_url"]+"/chat", headers={"Content-Type": "application/json"}, data=dat).json()
  except:
    return "[ChatGPT] 连接故障！"
  if "response" not in response:
    return json.dumps(response)
  else:
    response = html.unescape(response["response"])
    return response
gVar.func["get_chatgpt"] = get_chatgpt

def get_gpt4(text, user_name=None, chat_id="temp"):
  post_json = {
    "message": f"{user_name}:{text}",
    "user": str(user_name),
    "bot_id": str(gVar.self_id),
    "chat_id": str(chat_id)
  }
  if gVar.is_debug: printf(f"调用 GPT4Free API (/chat)：{post_json}")
  dat = json.dumps(post_json)
  response = ""
  try:
    response = requests.post(config["gpt4_url"]+"/chat", headers={"Content-Type": "application/json"}, data=dat).json()
  except:
    return "[GPT4Free] 连接故障！"
  if "response" not in response:
    return json.dumps(response)
  else:
    # response = html.unescape(response["response"])
    return response
gVar.func["get_gpt4"] = get_gpt4

def reset_chatgpt_conv(chat_id):
  post_json = {
    "convo_id": chat_id
  }
  if gVar.is_debug: printf(f"调用 ChatGPT API (/reset)：{post_json}")
  dat = json.dumps(post_json)
  response = ""
  try:
    response = requests.post(config["chatgpt_url"]+"/reset", headers={"Content-Type": "application/json"}, data=dat)
  except:
    return False
  if response.status_code == 200:
    return True
  else:
    return False

def get_stable_diffusion(gen_json):
  try:
    response = requests.post(url=f"{config['webui_url']}{config['webui_api_path']}", json=gen_json)
  except Exception as e:
    return "[未开启AI画图，请联系管理员开启！]"
  if response.status_code == 504:
    return f"[未开启AI画图，请联系管理员开启！]"
  elif response.status_code != 200:
    return f"[AI画图连接故障：{response.text}]"

  r = response.json()

  image = r["images"][0].split(",", 1)[0]
  image_info = json.loads(r["info"])
  return f"[CQ:image,file=base64://{image}]"

def edgegpt_avalible():
  if gVar.is_debug: printf(f"调用 EdgeGPT API (/avalible)")
  try:
    response = requests.get(config["edgegpt_url"]+"/avalible")
    if response.status_code == 200:
      return True
    else:
      return False
  except:
    return False

def get_edgegpt(text, user_name, chat_id):
  post_json = {
    "message": f"{text}",
    "user": str(user_name),
    "bot_id": str(gVar.self_id),
    "chat_id": str(chat_id)
  }
  if gVar.is_debug: printf(f"调用 EdgeGPT API (/chat)：{post_json}")
  dat = json.dumps(post_json)
  response = ""
  try:
    response = requests.post(config["edgegpt_url"]+"/chat", headers={"Content-Type": "application/json"}, data=dat).json()
  except:
    return "[New Bing] 连接故障！"
  if "response" not in response:
    return json.dumps(response)
  else:
    msg = html.unescape(response["response"])
    refer = ""
    if "refer" in response:
      for r in response.get("refer", ""):
        title = response["refer"][r]["title"]
        url = response["refer"][r]["url"]
        refer += f"[{r}] {title} [{url}]\n"
      if refer:
        refer += "\n"
      max_conv_times = response.get("max_conv_times", "20")
      conv_times = response.get("conv_times", "0")
      return f"{msg}\n\n{refer}本会话聊天{conv_times}/{max_conv_times}"
    return msg

def reset_edgegpt_conv(chat_id):
  post_json = {
    "convo_id": chat_id
  }
  if gVar.is_debug: printf(f"调用 EdgeGPT API (/reset)：{post_json}")
  dat = json.dumps(post_json)
  response = "[New Bing] 连接故障！"
  try:
    response = requests.post(config["edgegpt_url"]+"/reset", headers={"Content-Type": "application/json"}, data=dat).json()
  except:
    return str(response)
  if "response" in response and response["response"]:
    return "[New Bing] " + response["response"]
  else:
    return str(response)

def temp_chatgpt(text):
  post_json = {
    "message": f"{text}",
    "bot_id": str(gVar.self_id)
  }
  if gVar.is_debug: printf(f"调用 ChatGPT API (/temp_chat)：{post_json}")
  dat = json.dumps(post_json)
  try:
    response = requests.post(config["chatgpt_url"]+"/temp_chat", headers={"Content-Type": "application/json"}, data=dat).json()
    response = html.unescape(response["response"])
  except:
    response = ""
  return response
gVar.func["temp_chatgpt"] = temp_chatgpt



module_enable(module_name, chatgpt)