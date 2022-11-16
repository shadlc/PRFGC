# !/usr/bin/python
# 图片模块处理
# Pixiv功能需搭载HibiAPI使用

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

import re
import json
import time
import asyncio
import requests
import threading
from PicImageSearch.sync import *
from PicImageSearch.model import *

module_name = '图片模块'

data_file = 'data/image_data.json'
config = import_json(data_file)
saucenao_api = ''
api_url = config['api_url'] if 'api_url' in config else 'http://127.0.0.1:10777/api/'
setu_pattern = re.compile(r'(张|要|来|发|看|给|有没有|色|瑟|涩|se)\S*(图|色|瑟|涩|se|好看|好康|可爱)')
not_enough_pattern = re.compile(r'(完全|根本|一点也|不够|不太|不行|更|超|很|再|无敌|加大|没好|就这)')

class image:
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
    if self.owner_id not in config:
    	config[self.owner_id] = {'R18':False}
    self.config = config[self.owner_id] 

    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=2 and re.search(r'^图功能$', self.rev_msg): self.image_help(auth)
      elif auth<=2 and re.search(r'^(生成|转化)?二维码', self.rev_msg): self.qr_code()
      elif auth<=2 and re.search(r'(SauceNao|saucenao)', self.rev_msg): asyncio.new_event_loop().run_until_complete(self.image_search('saucenao'))
      elif auth<=2 and re.search(r'(是什么番|TraceMoe|tracemoe)', self.rev_msg): asyncio.new_event_loop().run_until_complete(self.image_search('tracemoe'))
      elif auth<=2 and re.search(r'(谷歌识图|谷歌搜图)', self.rev_msg): asyncio.new_event_loop().run_until_complete(self.image_search('google'))
      elif auth<=2 and re.search(r'(百度识图|百度搜图)', self.rev_msg): asyncio.new_event_loop().run_until_complete(self.image_search('baidu'))
      elif auth<=2 and re.search(r'^以图搜图', self.rev_msg): asyncio.new_event_loop().run_until_complete(self.image_search())
      elif auth<=2 and re.search(r'^图\S*排行', self.rev_msg): self.pixiv_rank()
      elif auth<=2 and re.search(r'^(搜图|查图|找图|寻图)', self.rev_msg): self.pixiv_search()
      elif auth<=2 and re.search(r'^图\s+', self.rev_msg): self.pixiv_get()
      elif auth<=1 and re.search(r'^图(\S*)?R18', self.rev_msg): self.R18_mode()
      elif auth<=2 and re.search(setu_pattern, self.rev_msg): self.lolicon_image(0)
      elif auth<=2 and re.search(not_enough_pattern, self.rev_msg) and re.search(setu_pattern, str(self.data.past_message)): self.lolicon_image(1)
      else: self.success = False
    else: self.success = False

  def image_help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=2:
      msg += '\n二维码 [内容文字] |生成二维码'
      msg += '\n图[排行类别]排行 (页数) |查看图片热门排行'
      msg += '\n搜图 [标签] (收藏数) (页数) |使用标签搜索图片'
      msg += '\n图 [PID] |获取指定pid图片信息'
      msg += '\n[以图搜图|百度识图|谷歌识图|SauceNao|TraceMoe] |以图搜图'
    reply(self.rev,msg)

  def qr_code(self):
    if re.search(r'^(生成|转化)?二维码\s(.*)', self.rev_msg):
      inputs = re.search(r'^(生成|转化)?二维码\s?(\S*)\s?([0-9]*)?\s?(L|M|Q|H)?\s?(\S*)?\s?(\S*)?', self.rev_msg).groups()
      text = inputs[1] if inputs[1] else ''
      size = inputs[2] if inputs[2] else '200'
      level = inputs[3] if inputs[3] else 'H'
      fgcolor = inputs[4].replace('#','') if inputs[4] else 'black'
      bgcolor = inputs[5].replace('#','') if inputs[5] else 'white'

      get_dict = {"text":text, "size":size, "level":level, "fgcolor":fgcolor, "bgcolor":bgcolor}
      if re.search(r'logo$', self.rev_msg):
        for rev in self.data.past_message:
          if re.search(r'\[CQ:image\S+url=(\S+)\]', rev['raw_message']):
            logo = re.search(r'\[CQ:image\S+url=(\S+)\]', rev['raw_message']).groups()[0]
            get_dict['logo'] = logo

      file_url = get_qrcode_respond(get_dict)
      if 'logo' == fgcolor:
        get_dict['fgcolor'] = 'black'
        get_dict['bgcolor'] = 'white'
        file_url = get_qrcode_respond(get_dict)
        msg = f'[CQ:image,file={file_url}]'
      elif '.png' not in file_url:
        msg = '颜色参数错误或logo大于二维码！'
      else:
        msg = f'[CQ:image,file={file_url}]'
    else:
      msg = '请使用 二维码 [内容文字] [大小(200)] [冗余度:L/M/Q/(H)] [前景颜色(black)] [背景颜色(white)] 来生成二维码，如果需添加LOGO，请先发送一张图片，然后在所有参数都输入最后额外添加"logo"来将其作为LOGO'
    reply(self.rev,msg)

  async def image_search(self, use_type=None):
    if use_type:
      search_type = use_type
    else:
      search_type = re.search(r'^以图搜图\s?(\S*)', self.rev_msg).groups()[0]
    image_url = ''
    proxies = 'http://127.0.0.1:7890'
    for rev in self.data.past_message:
          if re.search(r'\[CQ:image\S+url=(\S+)\]', rev['raw_message']):
            image_url = re.search(r'\[CQ:image\S+url=(\S+)\]', rev['raw_message']).groups()[0]
    try:
      if image_url == '':
        msg = '请先发送一图片之后再使用以图搜图功能，可搜索类型有saucenao、tracemoe、谷歌识图、百度识图'
      elif search_type == 'saucenao':
        msg = await image_search_saucenao(image_url)
      elif search_type == 'tracemoe':
        msg = await image_search_tracemoe(image_url)
      elif search_type == 'google':
        msg = await image_search_google(image_url, proxies)
      else:
        msg = await image_search_baidu(image_url)
    except:
      msg = '无法访问该网站进行搜索~'
      
    if msg == '':
      msg = f'%ROBOT_NAME%也没有见过这个呢~'
    reply(self.rev,msg)


  def pixiv_rank(self):
    resp = get_pixiv_respond({})
    if not resp:
      msg = 'Pixiv API无响应~'
      reply(self.rev,msg)
      return

    rank_type_dict = {'月':'month', '周':'week', '日':'day', '男性':'day_male', '女性':'day_female', '新人':'week_rookie', '原创':'week_original'}
    r18_mode = False
    if config[self.owner_id]['R18'] and re.search(r'R-18', self.rev_msg):
      r18_mode = True
    rank_type = re.search(r'图(\S*)?排行', self.rev_msg).groups()[0]
    if rank_type and rank_type in rank_type_dict:
      if (page := re.search(r'图\S*排行\s*([0-9]*)', self.rev_msg).groups()[0]): pass
      else: page = 1
      resp = get_pixiv_respond({'type':'rank', 'mode':rank_type_dict[rank_type], 'page':page})
      if 'illusts' not in resp:
        if 'error' in resp and 'OAuth' in resp['error']['message']:
          msg = f'token失效，请联系管理员!'
        elif 'code' in resp and 'detail' in resp:
         msg = resp['detail']
        else:
          msg = f'未知错误'
      else:
        reply(self.rev,QA_get('!!处理中') + f'共有{len(resp["illusts"])}张图片~')
        msg = f'Pixiv{rank_type}排行第{page}页\n\n'
        image_times = 0
        for illust in resp["illusts"]:
          if r18_mode or illust['sanity_level'] != 6:
            image_times+=1
            url = filter_pixiv_url(illust)
            msg += f'\n{image_times}.{illust["user"]["name"]}的作品\n{illust["title"]}({illust["id"]})\n[CQ:image,file={url["example_url"]}]'
    else:
      msg = f'可查询的排行类别有{list(rank_type_dict.keys())}，如[图月排行]'
    time.sleep(1)
    reply(self.rev,msg)

  def pixiv_search(self):
    if re.search(r'^(搜图|查图|找图|寻图)\s(\S+)\s*[0-9]*\s*([0-9]+:[0-9]+)*', self.rev_msg):

      resp = get_pixiv_respond({})
      if not resp:
        msg = 'Pixiv API无响应~'
        reply(self.rev,msg)
        return

      inputs = re.search(r'^(搜图|查图|找图|寻图)\s(\S+)\s*([0-9]*)\s*([0-9]+(:|：)[0-9]+|[0-9]*)', self.rev_msg).groups()
      words = inputs[1].replace('#',' ')
      min_bookmarks = int(inputs[2]) if inputs[2] else 5000
      page_range = inputs[3] if inputs[3] else ''
      r18_mode = False
      pages = 1
      page_min = 1
      page_max = 10
      page_valid = 1
      if config[self.owner_id]['R18'] and re.search(r'R-18', self.rev_msg):
        r18_mode = True
      if min_bookmarks >= 50000:
        words += ' 50000users入り'
      elif min_bookmarks >= 30000:
        words += ' 30000users入り'
      elif min_bookmarks >= 10000:
        words += ' 10000users入り'
      elif min_bookmarks >= 5000:
        words += ' 5000users入り'
      elif min_bookmarks >= 3000:
        words += ' 3000users入り'
      elif min_bookmarks >= 1000:
        words += ' 1000users入り'
      if re.search(r'[0-9]+(:|：)[0-9]+', page_range):
        temp = re.search(r'([0-9]+)(:|：)([0-9]+)', page_range).groups()
        pages = 0
        page_min = int(temp[0])
        page_max = int(temp[2])
      elif page_range:
        pages = int(page_range)

      msg = QA_get('!!处理中')+'寻找资源中~'
      if page_max - page_min > 100:
        msg += '\n请注意！过多页数会对服务器造成严重负担，已限制页数在100以内'
        page_max = page_min + 99
      reply(self.rev,msg)
      time.sleep(1)

      if pages:
        resp = get_pixiv_respond({'type':'search', 'word':words, 'page':pages})
      else:
        resp = get_pixiv_respond({'type':'search', 'word':words, 'page':page_min})
        thread = {}
        for p in range(page_min+1, page_max+1):
          thread[p] = (myThread(get_pixiv_respond,[{'type':'search', 'word':words, 'page':p}]))
          thread[p].start()
        for p in range(page_min+1, page_max+1):
          temp = thread[p].get_resp()
          if 'illusts' in temp and temp['illusts'] != '':
            page_valid +=1
            resp['illusts'] += temp['illusts']
        
      if 'illusts' not in resp:
        if 'error' in resp and 'OAuth' in resp['error']['message']:
          msg = f'token失效，请联系管理员!'
        elif 'code' in resp and 'detail' in resp:
         msg = resp['detail']
        else:
          msg = f'未找到符合要求的图片，可以尝试修改标签或者增改页数'
      else:
        illusts = []
        for illust in resp['illusts']:
          if illust['type'] == 'illust' and 'total_bookmarks' in illust and illust['total_bookmarks'] >= min_bookmarks:
            illusts.append(illust)
        time.sleep(1)
        if len(illusts):
          reply(self.rev, f'共寻找到{len(illusts)}张符合要求的图片，整理中~\n请注意！超过30张将可能无法发送~')
          msg = f'Pixiv搜索页面\n标签:{words}\n收藏数大于：{min_bookmarks}\n已筛选张数：{len(resp["illusts"])}\n有效页数：{page_valid}\n有效张数：{len(resp)}\n\n'
          image_times = 0
          for illust in illusts:
            if r18_mode or illust['sanity_level'] != 6:
              image_times+=1
              url = filter_pixiv_url(illust)
              msg += f'\n{image_times}.{illust["user"]["name"]}的作品\n{illust["title"]}({illust["id"]})\n[CQ:image,file={url["example_url"]}]'
        else:
          msg = f'已在{page_valid}张有效页内筛选{len(resp["illusts"])}张图，但是仍未找到符合要求的图片，可以尝试将收藏数降低'
    else:
      msg = '请使用 搜图 [标签] (最低收藏数(5000)) (页数(1)) 进行图片搜索，多标签前请用#分割'
    reply(self.rev, msg)

  def pixiv_get(self):
    resp = get_pixiv_respond({})
    if not resp:
      msg = 'Pixiv API无响应~'
      reply(self.rev,msg)
      return

    illust_type_dict = {'illust':'插画', 'manga':'漫画', 'ugoira':'视频'}
    if (illust_id := re.search(r'^图\s([0-9]*)', self.rev_msg).groups()[0]):
      resp = get_pixiv_respond({'type':'illust', 'id':illust_id, 'accept-language':'zh-cn'})
      if 'error' in resp and 'OAuth' in resp['error']['message']:
        msg = f'token失效，请联系管理员!'
      elif 'code' in resp and 'detail' in resp:
       msg = resp['detail']
      elif 'illust' not in resp:
        msg = '该作品已被删除，或作品ID不存在'
      else:
        illust = resp['illust']
        url = filter_pixiv_url(illust)
        msg = f'作品名：{illust["title"]}(pid:{illust["id"]})'
        msg += f'\n作者：{illust["user"]["name"]}(uid:{illust["user"]["id"]})'
        msg += f'\n上传日期：{illust["create_date"]}'
        msg += f'\n图片大小(宽x高)：{illust["width"]}x{illust["height"]}'
        msg += f'\n类型：{illust_type_dict[illust["type"]]}'
        msg += f'\n绘制软件：{illust["tools"]}'
        msg += f'\n收藏次数：{illust["total_bookmarks"]}'
        msg += f'\n浏览次数：{illust["total_view"]}'
        msg += f'\n评论数量：{illust["total_comments"]}'
        msg += f'\n标签：'
        for tag in illust["tags"]:
          msg += f'[{tag["name"]}({tag["translated_name"]})] '
        msg += f'\nPixiv地址：{url["pixiv_url"]}'
        msg += f'\n图片直链:{url["source_url"]}'
        msg += f'\n[CQ:image,file={url["source_url"]}]'
    else:
      msg = f'请使用 图 [PID] 获取图片信息'
    reply(self.rev,msg)

  def R18_mode(self):
    flag = self.config['R18']
    text = '开启' if self.config['R18'] else '关闭'
    if re.search(r'(开启|打开|启用|允许)', self.rev_msg):
      flag = True
      text = '开启'
    elif re.search(r'(关闭|禁止|不允许|取消)', self.rev_msg):
      flag = False
      text = '关闭'
    msg = f'R18开关已{text}'
    self.config['R18'] = flag
    data_save(self.owner_id, self.config)
    reply(self.rev,msg)

  def lolicon_image(self,r18):
    tags = ''
    if len(self.rev_msg.split(' '))>1:
      for tag in self.rev_msg.split(' ')[1:]:
        tags += '&tag=' + tag
    if self.config['R18'] and re.search(not_enough_pattern, self.rev_msg): r18=1
    resp = get_lolicon_image(r18, tags)
    if resp != '':
      author = f'{resp["author"]}(uid:{resp["uid"]})'
      title = f'{resp["title"]}(pid:{resp["pid"]})'
      url = resp['urls']['regular']
      msg = f'来自画师{author}的作品{title}[CQ:image,file={url}]'
    else:
      msg = '未找到该标签的图片'
    reply(self.rev, msg)

class myThread(threading.Thread):
  def __init__(self,func,args=()):
    super(myThread, self).__init__()
    self.func = func
    self.args = args
    self.done = False
  def run(self):
    self.resp = self.func(*self.args)
    self.done = True
  def get_resp(self):
    while not self.done: pass
    return self.resp

def data_save(owner_id, one_config):
  config[owner_id] = one_config
  save_json(data_file, config)

def get_lolicon_image(r18=0,tags=''):
  """
  获取LoliconAPI图片
  :param r18: 是否获取R18图片
  :param tags: 需要筛选的标签
  :return: 图片链接
  """
  url = 'https://api.lolicon.app/setu/v2'
  url += f'?size=regular&r18={r18}{tags}'
  resp = json.loads(requests.get(url).text)
  if gVar.is_debug: printf(f'调用LoliconAPI返回结果：{resp}')
  if resp['data'] == []:
    return ''
  else:
    return resp['data'][0]

def filter_pixiv_url(illust):
  """
  从pixiv返回的单个图片json中筛选url
  :param illust: 单个图片json
  :return: 链接数组
  """
  pixiv_url = f'https://www.pixiv.net/artworks/{illust["id"]}'
  example_url = illust["image_urls"]["square_medium"].replace('i.pximg.net','i.pixiv.re')
  if illust["meta_single_page"]:
    source_url = illust["meta_single_page"]["original_image_url"].replace('i.pximg.net','i.pixiv.re')
  else:
    source_url = illust["meta_pages"][0]["image_urls"]["original"].replace('i.pximg.net','i.pixiv.re')
  return {'pixiv_url':pixiv_url, 'example_url':example_url, 'source_url':source_url}

def get_pixiv_respond(params):
  """
  进行Pixiv接口访问
  :param params: 字典类型的请求参数
  :return: GET响应传入字典
  """
  url = f'{api_url}pixiv/'
  if 'type' in params:
    url += f'{params["type"]}?'
    del params["type"]
  for param_name, param_value in params.items():
    url += f'{param_name}={param_value}&'
  url = url[:-1]
  try:
    r = requests.get(url)
    r.encoding='utf-8'
    resp = json.loads(r.text)
    if gVar.is_debug: warnf(f'{[module_name]} 向{LPURPLE}HibiAPI{RESET}访问{url}')
    return resp
  except:
    errorf(f'{[module_name]} 访问 {url} 出错')
    return ''

def get_qrcode_respond(params):
  """
  进行hipiapi QRCode接口访问
  :param params: 字典类型的请求参数
  :return: 返回图片链接地址
  """
  url = f'{api_url}qrcode?'
  for param_name, param_value in params.items():
    url += f'{param_name}={param_value}&'
  printf(url)
  r = requests.get(url[:-1])
  return r.url

async def image_search_saucenao(image_url, proxies=None):
  if saucenao_api == '': msg = '请先前往[https://saucenao.com/user.php?page=search-api]获取APIKey'
  resp = await SauceNAO(api_key=saucenao_api, proxies=proxies).search(image_url)
  images = resp.raw
  if num := len(images):
    msg = f'使用SauceNAO搜索到了{num}个结果\n'
    for i in range(len(images)):
      msg += f'\n标题: {images[i].title}'
      msg += f'\n作者: {images[i].author}'
      msg += f'\n相似度: {images[i].similarity}%'
      msg += f'\n图片地址: {images[i].url}'
      if 'source' in (data := resp.origin['results'][i]['data']):
        msg += f'\n原图地址: {data["source"]}'
      msg += f'\n[CQ:image,file={images[i].thumbnail}]'
      msg += f'\n'
    return msg
  else:
    return ''

async def image_search_tracemoe(image_url, proxies=None):
  resp = await TraceMoe(proxies=proxies).search(image_url)
  anims = resp.raw
  if num := len(anims):
    msg = f'使用TraceMoe搜索到了{num}个结果\n\n'
    for i in anims:
      if i.isAdult:
        msg += '\n警告！！！这是一个里番'
      msg += f'\n番剧名称: {i.title_native}'
      msg += f'\n番剧中文名: {i.title_chinese}'
      msg += f'\n番剧罗马音名: {i.title_romaji}'
      msg += f'\n相似度: {i.similarity}%'
      msg += f'\n在剧中第{i.episode}集的{time_format(i.From)}到{time_format(i.To)}'
      msg += f'\n[CQ:image,file={i.image}]'
      msg += f'\n'
    return msg
  else:
    return ''

async def image_search_google(image_url, proxies=None):
  resp = await Google(proxies=proxies).search(image_url)
  images = resp.raw
  if num := len(images):
    msg = f'使用谷歌识图搜索到了{num}个结果\n\n'
    for i in images:
      msg += f'\n{i.title}'
      msg += f'\n链接: {i.url}'
      msg += f'\n'
    return msg
  else:
    return ''

async def image_search_baidu(image_url, proxies=None):
  resp = await BaiDu(proxies=proxies).search(image_url)
  images = []
  for i in resp.similar:
    if 'titles' in i and 'simi' in i:
      images.append(i)
  if num := len(images):
    msg = f'使用百度识图搜索到了{num}个结果\n'
    for i in images:
      msg += f'\n{i["titles"]}'
      msg += f'\n相似度: {i["simi"][:5]}%'
      msg += f'\n原文地址: {i["titles_url"]}'
      msg += f'\n[CQ:image,file={i["imgs_url"]}]'
      msg += f'\n'
    return msg
  else:
    return '百度识图暂无结果~\n如果是动漫图片可以使用 SauceNao 进行搜索'

def time_format(seconds):
  m, s = divmod(int(seconds), 60)
  h, m = divmod(m, 60)
  #return f'{h:d}:{m:02d}:{s:02d}'
  return f'{m:02d}:{s:02d}'


module_enable(module_name, image)