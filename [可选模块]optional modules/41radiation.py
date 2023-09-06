#!/usr/bin/python
#辐射量检测模块处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

import os
import json
import requests
from pyecharts import options as opts
from pyecharts.charts import Map
from pyecharts.faker import Faker
from pyecharts.globals import CurrentConfig

base_url = ""
base_www_dir = "/var/www/rad/"
CurrentConfig.ONLINE_HOST = f"{base_url}lib/js/"
province = {
  "广东省": "广东",
  "安徽省": "安徽",
  "福建省": "福建",
  "甘肃省": "甘肃",
  "贵州省": "贵州",
  "海南省": "海南",
  "河北省": "河北",
  "黑龙江省": "黑龙江",
  "河南省": "河南",
  "湖北省": "湖北",
  "湖南省": "湖南",
  "江苏省": "江苏",
  "江西省": "江西",
  "吉林省": "吉林",
  "辽宁省": "辽宁",
  "青海省": "青海",
  "山东省": "山东",
  "山西省": "山西",
  "陕西省": "陕西",
  "四川省": "四川",
  "台湾省": "台湾",
  "云南省": "云南",
  "浙江省": "浙江",
  "内蒙古自治区": "内蒙",
  "宁夏回族自治区": "宁夏",
  "广西壮族自治区": "广西",
  "新疆维吾尔自治区": "新疆",
  "西藏自治区": "西藏",
  "香港特别行政区": "香港",
  "澳门特别行政区": "澳门",
  "重庆市": "重庆",
  "北京市": "北京",
  "天津市": "天津",
  "上海市": "上海"
}

module_name = "辐射检测模块"

class radiation:
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
    
    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if re.search(r'^辐射检测功能$',self.rev_msg): self.help(auth)
      elif auth<=3 and re.search(r'(\S*)\s*辐射(量|度|值)$',self.rev_msg): self.query()
      else: self.success = False
    else: self.success = False

  def help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=3:
      msg += '\n(全国|城市名) [辐射量] | 获取指定城市辐射量'
    reply(self.rev, msg)

  def query(self):
    msg = ''
    timestr = ''
    city = re.search(r'(\S*)\s*辐射(量|度|值)', self.rev_msg).groups()[0]
    if not city:
      city = '全国'
    if city == '全国' or city in province.keys() or city in province.values():
      result = request_radiation('province')
      if result.get("code") != 200:
        msg = f'获取数据出错！错误码：{result.get("code")}\n原因：{result.get("result")}'
        reply(self.rev, msg)
        return
    else:
      result = request_radiation()
    data = result.get("data")

    if city == '全国':
      if base_url == '':
        msg +=  '未设置服务器网页路径，暂时无法展示地图'
      url = render_map(data)
      msg += f'全国空气吸收剂量率：\n{url}'
    elif city in province.keys() or city in province.values():
      for item in data:
        if item and re.search(r'^' + item.get('name'), city):
          name = item.get('name')
          station = item.get('station')
          val = item.get('val')
          unit = item.get('unit')
          timestr = '\n--' + item.get('time')
          msg += f'{name}({station})的辐射剂量率为{val}{unit}\n'
    else:
      for item in data:
        if item and re.search(r'^' + city, item.get('name')):
          name = item.get('name')
          provname = item.get('provname')
          val = item.get('val')
          unit = item.get('unit')
          timestr = '\n--' + item.get('time')
          itemname = item.get('itemname')
          msg += f'{provname}({name})的{itemname}为{val}{unit}\n'
    if msg:
      msg += f'{timestr}\n-- 数据来源 中国辐射环境监测网[https://data.rmtc.org.cn]'
      reply(self.rev, msg)
    else:
      msg = '未查询到该地区的数据！'
      reply(self.rev, msg)

def request_radiation(query_type='all'):
  data = []
  try:
    if query_type == 'province':
      data_type = 'province'
      res = requests.post(
          'https://data.rmtc.org.cn/gis/DoAction.action',
          data = '{"action":"doDataRequest","dest":"curProvData","operation":"query","parameter":{"type":0}}'
      )
    else:
      data_type = 'all'
      res = requests.post(
          'https://data.rmtc.org.cn/gis/DoAction.action',
          data = '{"action":"doDataRequest","dest":"stationList","operation":"query","parameter":{"type":-1}}'
      )
    resource = json.loads(res.text)
    code = res.status_code
    result = resource.get('result')
    if code == 200 and result == 'success':
      data = resource.get('data').get('list')
    return {'code': code, 'result': result, 'data_type': data_type, 'data': data}
  except Exception as e:
    return {'code': 500, 'result': f'内部错误\n{e}', 'data_type': 'None', 'data': data}

def render_map(raw_data):
  data = [(i.get('name'), i.get('val')) for i in raw_data]
  date = raw_data[0].get('time')
  map = Map(init_opts = opts.InitOpts(width="1200px", height="741.6px", page_title="全国空气吸收剂量率"))
  map.add(
    series_name = "全国空气吸收剂量率(nGy/h)",
    data_pair = data,
    name_map = province,
    maptype = "china",
    label_opts=opts.LabelOpts(is_show=True),
    is_map_symbol_show = True,
  )
  map.set_global_opts(visualmap_opts=opts.VisualMapOpts(max_=200,is_piecewise=True))
  path = f'{base_www_dir}{date}/'
  if not os.path.exists(path):
    os.makedirs(path)
  map.render(f'{path}index.html')
  return f'{base_url}rad/{date}'

def image_save(file_name,file):
  image_dir = gVar.data_dir + '/images'
  if not os.path.exists(image_dir):
    raise RuntimeError('CQHttp数据文件夹设置不正确！')
  if not os.path.exists(f'{image_dir}/radiation'):
    os.mkdir(f'{image_dir}/radiation')
  open(f'{image_dir}/radiation/{file_name}', mode="wb").write(file)
  return f'{image_dir}/radiation/{file_name}'

def detect_image(file_name):
  image_dir = gVar.data_dir + '/images'
  if not os.path.exists(image_dir):
    raise RuntimeError('CQHttp数据文件夹设置不正确！')
  if not os.path.exists(f'{image_dir}/radiation/{file_name}'):
    return False
  return True

module_enable(module_name, radiation)