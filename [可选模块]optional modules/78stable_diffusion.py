#!/usr/bin/python
#StableDiffusion模块处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

import json

module_name = 'StableDiffusion模块'
webui_url = "http://192.168.163.254/webui"
webui_api_path = "/sdapi/v1/txt2img"
default_json = {
  "prompt": "masterpiece, best quality, ",
  "steps": 20,
  "width": 512,
  "height": 512,
  "cfg_scale": 7,
  "sampler_index": "DPM++ 2M Karras",
  "seed": -1,
  "negative_prompt": "nsfw,{Multiple people},lowres,bad anatomy,bad hands, text, error, missing fingers,extra digit, "
                     "fewer digits, cropped, worstquality, low quality, normal quality,jpegartifacts,signature, "
                     "watermark, username,blurry,bad feet,cropped,poorly drawn hands,poorly drawn face,mutation,"
                     "deformed,worst quality,low quality,normal quality,jpeg artifacts,signature,watermark,"
                     "extra fingers,fewer digits,extra limbs,extra arms,extra legs,malformed limbs,fused fingers,"
                     "too many fingers,long neck,cross-eyed,mutated hands,polar lowres,bad body,bad proportions,"
                     "gross proportions,text,error,missing fingers,missing arms,missing legs,extra digit"
}

class stable_diffusion:
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
    # if self.group_id:
    #   self.owner_id = f'g{self.group_id}'
    # else:
    #   self.owner_id = f'u{self.user_id}'
    # self.data = gVar.data[self.owner_id]

    #检测开头&号触发
    if re.search(r'^&amp;\S+', self.rev_msg):
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=2: self.stable_diffusion()
      else: self.success = False
    else: self.success = False

  def stable_diffusion(self):
    reply(self.rev, "正在生成中...")
    gen_json = default_json.copy()
    gen_json["prompt"] += self.rev_msg[5:]
    code, image = get_stable_diffusion(gen_json)
    if code != 200:
      msg = f"{code} {image}"
      reply(self.rev,msg)
    else:
      msg = f"[CQ:image,file=base64://{image}]"
      reply(self.rev,msg)
    
def get_stable_diffusion(gen_json):
  try:
    response = requests.post(url=f'{webui_url}{webui_api_path}', json=gen_json)
  except Exception as e:
    return 500, "未开启AI画图，请联系lc开启！"

  if response.status_code != 200:
    return response.status_code, response.text

  r = response.json()

  image = r['images'][0].split(",", 1)[0]
  image_info = json.loads(r["info"])
  return 200, image





if webui_url == '':
  warnf(f'[{module_name}] 模块已禁用，如需启用请先搭建WebUI')
else:
  module_enable(module_name, stable_diffusion)