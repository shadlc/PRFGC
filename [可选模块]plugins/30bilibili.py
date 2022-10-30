#!/usr/bin/python
#VUP杀群模块处理

import global_variable as gVar
from ifunction import *
from api_cqhttp import *

import re
import os
import sys
import time
import asyncio
import threading
import configparser

import nest_asyncio
nest_asyncio.apply()

from playwright.__main__ import main
from playwright.async_api import Browser, async_playwright
from bilireq.grpc.dynamic import grpc_get_user_dynamics
from bilireq.live import get_rooms_info_by_uids


module_name = '哔哩哔哩模块'

data_file = 'data/bilibili_data.json'
follow_list = import_json(data_file)
loop = asyncio.get_event_loop()
live_status = {}
past_dynamics = {}
today = time.gmtime().tm_yday
bilibili_thread = threading.Thread(daemon=True)
bilibili_thread_running = True

class bilibili:
  def __init__(self,rev,auth):
    self.success = True
    self.rev = rev
    self.dynamic_type = self.rev['dynamic_type'] if 'dynamic_type' in self.rev else ''
    self.dynamic_time = self.rev['time'] if 'time' in self.rev else ''
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

    if self.group_id:
      self.owner_id = f'g{self.group_id}'
    else:
      self.owner_id = f'u{self.user_id}'
    self.follow_list = follow_list[self.owner_id] if self.owner_id in follow_list else {}

    #群聊@消息以及私聊消息触发
    if not self.group_id or gVar.at_info in self.rev_msg:
      if self.group_id: self.rev_msg = self.rev_msg.replace(gVar.at_info,'').strip()
      if auth<=3 and re.search(r'^B站功能$', self.rev_msg): self.bilibili_help(auth)
      elif auth<=3 and re.search(r'^关注列表$', self.rev_msg): self.show_follow_list()
      elif auth<=2 and re.search(r'^关注', self.rev_msg): self.subscribe()
      elif auth<=2 and re.search(r'^取关', self.rev_msg): self.unsubscribe()
      elif auth<=2 and re.search(r'^昵称', self.rev_msg): self.label()
      elif auth<=2 and re.search(r'^通知关键词', self.rev_msg): self.keywords()
      elif auth<=3 and re.search(r'^(\S+)\s?动态\s?(开启|关闭)?$', self.rev_msg): self.dynamic()
      elif auth<=3 and re.search(r'^(\S+)\s?直播\s?(开启|关闭)?$', self.rev_msg): self.live()
      elif auth<=3 and re.search(r'^(\S+)\s?粉丝数\s?(开启|关闭)?$', self.rev_msg): self.fans(auth)
      elif auth<=2 and re.search(r'^(\S+)\s?通知\s?(开启|关闭)$', self.rev_msg): self.setting()
      else: self.success = False
    else: self.success = False

  def bilibili_help(self, auth):
    msg = f'{module_name}%HELP%\n'
    if auth<=3:
      msg += '\n关注列表 |查看当前关注的UP主列表'
      msg += '\n[UP主] 动态 |获取UP主的最新动态'
      msg += '\n[UP主] 直播 |获取UP主的直播间状态'
      msg += '\n[UP主] 粉丝数 |查看该UP粉丝数'
      msg += '\n(开启|关闭)实时追踪 [UP主] 粉丝数 |实时追踪UP主粉丝数'
    if auth<=2:
      msg += '\n[UP主] 动态 [开启|关闭] |开关UP主动态通知'
      msg += '\n[UP主] 直播 [开启|关闭] |开关UP主直播通知'
      msg += '\n[UP主] 粉丝数 [开启|关闭] |开关UP主粉丝数通知'
      msg += '\n关注 [UP主] |关注一个新的UP主'
      msg += '\n取关 [UP主] |取关一个UP主'
      msg += '\n昵称 [UP主] [昵称] |给UP主取一个昵称'
      msg += '\n通知关键词 [UP主] [匹配规则] |设置通知过滤关键词(正则匹配)'
    reply(self.rev,msg)

  def show_follow_list(self):
    if self.follow_list != {}:
      if self.group_id:
        msg = f'本群的关注列表'
      else:
        msg = f'你的关注列表'
      for uid in self.follow_list:
        info = get_user_info(uid)
        if info:
          self.follow_list[uid]['name'] = info[1]
          self.follow_list[uid]['fans'] = info[2]
          self.follow_list[uid]['avatar'] = info[3]
        msg += f'\n===================='
        msg += print_user_data(uid, self.follow_list)
      follow_list_save(self.owner_id, self.follow_list)
    else:
        msg = f'这里还未拥有关注列表，请管理员添加吧~'
    reply(self.rev,msg)

  def subscribe(self):
    if (re.search(r'^关注\s?(\S+)$', self.rev_msg)):
      user = re.search(r'^关注\s?(\S+)$', self.rev_msg).groups()[0]
      info = get_info(user)
      if info:
        uid = info[0]
        name = info[1]
        fans = info[2]
        avatar = info[3]
        if uid and uid in self.follow_list:
          msg = f'你已经关注了{self.follow_list[uid]["name"]}'
        else:
          self.follow_list[uid] = {"name": name, "label": "", "avatar":avatar, "fans": fans, "keyword": "", "dynamic_notice": True, "live_notice": True, "fans_notice": False, "global_notice": True}
          follow_list_save(self.owner_id, self.follow_list)
          msg = f'已将{name}(UID:{uid})添加至关注列表'
        msg += f'\n===================='
        msg += print_user_data(uid, self.follow_list)
      else:
        msg = f'查无此人'
    else:
      msg = '请使用 关注 [UP主] 对UP主进行关注'
    reply(self.rev, msg)

  def unsubscribe(self):
    if (re.search(r'^取关\s?(\S+)$', self.rev_msg)):
      user = re.search(r'^取关\s?(\S+)$', self.rev_msg).groups()[0]
      info = get_info(user)
      if info:
        uid = info[0]
        name = info[1]
        if uid and uid not in self.follow_list:
          msg = f'你并没有关注{name}'
        else:
          msg = f'已将{name}(UID:{uid})取关'
          self.follow_list.pop(uid)
          follow_list_save(self.owner_id, self.follow_list)
      else:
        msg = f'查无此人'
    else:
      msg = '请使用 取关 [UP主] 进行取消关注UP主'
    reply(self.rev, msg)

  def label(self):
    if re.search(r'^昵称\s?(\S+)\s?(\S+)$', self.rev_msg):
      temp = re.search(r'^昵称\s?(\S+)\s?(\S+)$', self.rev_msg).groups()
      user = temp[0]
      nickname = temp[1]
      info = get_info(user)
      if info:
        uid = info[0]
        name = info[1]
        fans = info[2]
        avatar = info[3]
        if uid and uid in self.follow_list:
          self.follow_list[uid]["label"] = nickname
          follow_list_save(self.owner_id, self.follow_list)
          msg = f'已成功为{self.follow_list[uid]["name"]}设置昵称【{nickname}】'
        else:
          msg = '未关注该UP主，请先关注！'
      else:
        msg = f'查无此人'
    else:
      msg = '请使用 昵称 [UP主] [昵称] 为UP主取昵称'
    reply(self.rev, msg)

  def keywords(self):
    if re.search(r'^通知关键词\s?(\S+)\s+(\S+)$', self.rev_msg):
      temp = re.search(r'^通知关键词\s?(\S+)\s+(\S+)$', self.rev_msg).groups()
      user = temp[0]
      pattern = temp[1]
      info = get_info(user)
      if info:
        uid = info[0]
        name = info[1]
        if uid in self.follow_list:
          self.follow_list[uid]["keyword"] = pattern
          follow_list_save(self.owner_id, self.follow_list)
          msg = f'已成功为{name}设置正则匹配关键词【{pattern}】'
        else:
          msg = '未关注该UP主，请先关注！'
      else:
        msg = f'查无此人'
    else:
      msg = '请使用 通知关键词 [UP主] [关键词] 为UP主设置通知关键词'
    reply(self.rev, msg)

  def dynamic(self):
    if re.search(r'^(\S+)\s?动态\s?(开启|关闭)?$', self.rev_msg):
      temp = re.search(r'^(\S+)\s?动态\s?(开启|关闭)?$', self.rev_msg).groups()
      user = temp[0]
      flag = temp[1]
      info = get_info(user)
      if info:
        uid = info[0]
        name = info[1]
        if not name:
          name = '这个B\n站用户'
        if flag == None:
          dynamic = get_latest_dynamic(uid)
          if dynamic:
            name = dynamic[0]
            dynamic_id = dynamic[1]
            msg = f'{name}的最新一条动态：'
            msg += f'\nhttps://t.bilibili.com/{dynamic_id}'
            msg += f'\n[CQ:image,file=bilibili/{dynamic_id}.png]'
          else:
            msg = f'{name}没有发过任何动态...'
        elif flag == '开启':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['dynamic_notice'] = True
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已开启对{name}的动态观测~'
        elif flag == '关闭':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['dynamic_notice'] = False
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已关闭对{name}的动态观测~'
      else:
        msg = f'查无此人'
    else:
      msg = '请使用 [UP主] 动态 查看UP主最新动态'
    reply(self.rev, msg)

  def live(self):
    if re.search(r'^(\S+)\s?直播\s?(开启|关闭)?$', self.rev_msg):
      temp = re.search(r'^(\S+)\s?直播\s?(开启|关闭)?$', self.rev_msg).groups()
      user = temp[0]
      flag = temp[1]
      info = get_info(user)
      if info:
        uid = info[0]
        name = info[1]
        if flag == None:
          status = get_live_status(uid)
          if status:
            if status[0]:
              msg = f'{name}正在直播：'
              msg += f'\n{status[1]}'
              if status[2]:
                msg += f'\n[CQ:image,file={status[2]}]'
              msg += f'https://live.bilibili.com/{status[3]}'
              msg += f'\n已经直播了{time.strftime("%H小时%M分钟", time.gmtime(time.time()-int(status[4])))}，{status[5]}人在看'
              msg += f'\n========近期画面========'
              msg += f'\n[CQ:image,file={status[6]}]'
            else:
              msg = f'{name}在休息中哦~'
          elif name:
            msg = f'{name}从来没有直播过哦~'
          else:
            msg = f'查询失败（；´д｀）ゞ'
        elif flag == '开启':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['live_status'] = True
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已开启对{name}的直播通知~'
        elif flag == '关闭':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['live_status'] = False
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已关闭对{name}的直播通知~'
      else:
        msg = f'查无此人'
    else:
      msg = '请使用 [UP主] 动态 查看UP主最新动态'
    reply(self.rev, msg)

  def fans(self,auth):
    if re.search(r'^(\S+)\s?粉丝数\s?(开启|关闭)?$', self.rev_msg):
      temp = re.search(r'^(\S+)\s?粉丝数\s?(开启|关闭)?$', self.rev_msg).groups()
      user = temp[0]
      flag = temp[1]
      info = get_info(user)
      if not info:
        info = get_info(re.sub(r'(\S+)?实时追踪', '', user))
      if info:
        uid = info[0]
        name = info[1]
        fans = info[2]
        avatar = info[3]
        if auth<=2 and re.search(r'实时追踪', self.rev_msg):
          global bilibili_thread
          global bilibili_thread_running
          if re.search(r'(关闭|停止|取消|退出)', self.rev_msg):
            if bilibili_thread.is_alive():
              bilibili_thread_running = False
              msg = f'已关闭粉丝数实时追踪~'
            else:
              msg = f'暂未开启粉丝数实时追踪~'
          else:
            if bilibili_thread.is_alive():
              msg = f'请先关闭正在进行中的实时追踪~'
            else:
              bilibili_thread = threading.Thread(target=fans_check_loop, args=(uid, self.owner_id), daemon=True)
              bilibili_thread.start()
              msg = f'已开启对{name}的粉丝数实时追踪~(十秒检测一轮，粉丝数变动小于10不发送)'
        elif flag == None:
          msg = f'{name}当前的粉丝数为：{fans}'
          msg += f'\n[CQ:image,file={avatar}]'
        elif flag == '开启':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['fans_notice'] = True
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已开启对{name}的粉丝数通知~'
        elif flag == '关闭':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['fans_notice'] = False
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已关闭对{name}的粉丝数通知~'

      else:
        msg = f'查无此人'
    else:
      msg = '请使用 [UP主] 粉丝数 查看UP主粉丝数'
    reply(self.rev, msg)

  def setting(self):
    if re.search(r'^(\S+)\s?通知\s?(开启|关闭)$', self.rev_msg):
      temp = re.search(r'^(\S+)\s?通知\s?(开启|关闭)$', self.rev_msg).groups()
      user = temp[0]
      flag = temp[1]
      if user == "全部":
        status = True
        if flag == '开启':
          status = True
        elif flag == '关闭':
          status = False
        for uid in self.follow_list:
          self.follow_list[uid]['global_notice'] = status
        follow_list_save(self.owner_id, self.follow_list)
        msg = f'已{flag}全体UP主的通知~'
        reply(self.rev, msg)
        return

      info = get_info(user)
      if info:
        uid = info[0]
        if flag == '开启':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['global_notice'] = True
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已开启对{self.follow_list[uid]["name"]}的全部通知~'
        elif flag == '关闭':
          if uid not in self.follow_list:
            msg = '请先关注UP主~'
          else:
            self.follow_list[uid]['global_notice'] = False
            follow_list_save(self.owner_id, self.follow_list)
            msg = f'已关闭对{self.follow_list[uid]["name"]}的全部通知~'
      else:
        msg = f'查无此人'
    else:
      msg = '请使用 [UP主] 通知 [开启|关闭] 开关UP主的通知'
    reply(self.rev, msg)

class browser:

  def __init__(self,proxy=None, **kwargs):
    if proxy:
        kwargs["proxy"] = {"server": proxy}
    p = task(async_playwright().start())
    self._browser = task(p.chromium.launch(**kwargs))

  def get_browser(self):
    assert self._browser
    return self._browser

  async def get_dynamic_screenshot(self,dynamic_id, style="mobile"):
    if style.lower() == "mobile":
        return await self.get_dynamic_screenshot_mobile(dynamic_id)
    else:
        return await self.get_dynamic_screenshot_pc(dynamic_id)

  async def get_dynamic_screenshot_mobile(self,dynamic_id):
    """移动端动态截图"""
    url = f"https://m.bilibili.com/dynamic/{dynamic_id}"
    browser = self.get_browser()
    page = await browser.new_page(
        device_scale_factor=2,
        user_agent=(
            "Mozilla/5.0 (Linux; Android 10; RMX1911) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36"
        ),
        viewport={"width": 500, "height": 800},
    )
    try:
        await page.goto(url, wait_until="networkidle", timeout=10000)
        if page.url == "https://m.bilibili.com/404":
            return None
        await page.add_script_tag(
            # document.getElementsByClassName('m-dynamic-float-openapp').forEach(v=>v.remove());
            # document.getElementsByClassName('dyn-header__following').forEach(v=>v.remove());
            # document.getElementsByClassName('dyn-share').forEach(v=>v.remove());

            # const dyn = document.getElementsByClassName('card-wrap')[0];
            # dyn.style.width = 'auto';
            # dyn.style.padding = '20px';
            # dyn.style.backgroundImage= 'linear-gradient(to bottom right, #c8beff, #bef5ff)';

            # const content = document.getElementsByClassName('dyn-card')[0];
            # content.style.boxShadow = '0px 0px 10px 2px #fff';
            # content.style.border = '2px solid white';
            # content.style.borderRadius = '10px';
            # content.style.background = 'rgba(255,255,255,0.7)';
            # document.getElementsByClassName('dyn-content__orig')[0].style.backgroundColor = 'transparent';
            # content.style.fontFamily = 'Noto Sans CJK SC, sans-serif';
            # content.style.overflowWrap = 'break-word';

            # document.querySelectorAll('.dyn-draw__picture>img').forEach(v=>{ v.style.border = '2px solid white'; v.style.borderRadius = '10px'; });
            # document.getElementsByClassName('dyn-article__card').forEach(v=>{ v.style.border = '2px solid white'; v.style.borderRadius = '10px'; v.style.background = 'transparent'; });

            # document.getElementsByClassName('dyn-header__author__face').forEach(v=>{ v.style.borderRadius = '100%'; });
            # document.getElementsByClassName('dyn-article__card').forEach(v=>{ v.style.maxHeight = 'fit-content'; });
            # document.getElementsByClassName('dyn-article__covers__item').forEach(v=>v.style.margin = '10px');
            # const draws = document.getElementsByClassName('dyn-draw')[0];
            # draws.children.forEach(p=>{ p.style.padding = '5px'; p.children.forEach(v=>{ v.style.margin = '3px';total = (parseInt(getComputedStyle(p).width) - 10); count = (p.children.length); if(count < 4) {size = (total / count - 6);}else if(count == 4){size = (total / 2 - 6)}else{size = total / 3 - 6} v.style.width = size.toString() + 'px'; })});
            content=
            # 去除打开app按钮
            "document.getElementsByClassName('m-dynamic-float-openapp').forEach(v=>v.remove());"
            # 去除关注按钮
            "document.getElementsByClassName('dyn-header__following').forEach(v=>v.remove());"
            # 去除分享按钮
            "document.getElementsByClassName('dyn-share').forEach(v=>v.remove());"
            # 获取整个动态
            "const dyn = document.getElementsByClassName('card-wrap')[0];"
            # 修复宽度大小问题
            "dyn.style.width = 'auto';"
            "dyn.style.padding = '10px';"
            # 显示背景颜色
            "dyn.style.backgroundImage = 'linear-gradient(to bottom right, #c8beff, #bef5ff)';"
            # 获取内容
            "const content = document.getElementsByClassName('dyn-card')[0];"
            # 添加阴影与边框
            "content.style.boxShadow = '0px 0px 10px 2px #fff';"
            "content.style.border = '2px solid white';"
            "content.style.borderRadius = '10px';"
            # 文章主体毛玻璃
            "content.style.background = 'rgba(255,255,255,0.7)';"
            "document.getElementsByClassName('dyn-content__orig')[0].style.backgroundColor = 'transparent';"
            # 修复字体与换行问题
            "content.style.fontFamily = 'Noto Sans CJK SC, sans-serif';"
            "content.style.overflowWrap = 'break-word';"
            # 添加图片边框
            "document.querySelectorAll('.dyn-draw__picture>img').forEach(v=>{ v.style.border = '2px solid white'; v.style.borderRadius = '10px'; });"
            "document.getElementsByClassName('dyn-article__card').forEach(v=>{ v.style.border = '2px solid white'; v.style.borderRadius = '10px'; v.style.background = 'transparent'; });"

            # 修复内部元素大小
            "document.getElementsByClassName('dyn-header__author__face').forEach(v=>{ v.style.borderRadius = '100%'; });"
            "document.getElementsByClassName('dyn-article__card').forEach(v=>{ v.style.maxHeight = 'fit-content'; });"
            "document.getElementsByClassName('dyn-article__covers__item').forEach(v=>v.style.margin = '10px');"
            "const draws = document.getElementsByClassName('dyn-draw')[0];"
            "draws.children.forEach(p=>{ p.style.padding = '5px'; p.children.forEach(v=>{ v.style.margin = '3px';total = (parseInt(getComputedStyle(p).width) - 10); count = (p.children.length); if(count < 4) {size = (total / count - 6);}else if(count == 4){size = (total / 2 - 6)}else{size = total / 3 - 6} v.style.width = size.toString() + 'px'; })});"
        )
        card = await page.query_selector(".card-wrap")
        assert card
        clip = await card.bounding_box()
        assert clip
        return await page.screenshot(clip=clip, full_page=True)
    except Exception:
        printf(f"截取动态时发生错误：{url}")
        return await page.screenshot(full_page=True)
    finally:
        await page.close()

  async def get_dynamic_screenshot_pc(self,dynamic_id):
    """电脑端动态截图"""
    url = f"https://t.bilibili.com/{dynamic_id}"
    browser = self.get_browser()
    context = await browser.new_context(
        viewport={"width": 2560, "height": 1080},
        device_scale_factor=2,
    )
    await context.add_cookies(
        [
            {
                "name": "hit-dyn-v2",
                "value": "1",
                "domain": ".bilibili.com",
                "path": "/",
            }
        ]
    )
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=10000)
        if page.url == "https://www.bilibili.com/404":
            return None
        card = await page.query_selector(".card")
        assert card
        clip = await card.bounding_box()
        assert clip
        bar = await page.query_selector(".bili-dyn-action__icon")
        assert bar
        bar_bound = await bar.bounding_box()
        assert bar_bound
        clip["height"] = bar_bound["y"] - clip["y"]
        return await page.screenshot(clip=clip, full_page=True)
    except Exception:
        printf(f"截取动态时发生错误：{url}")
        return await page.screenshot(full_page=True)
    finally:
        await context.close()

def live_check(proxy=None):
  uids = get_uid_list("live")
  if not uids:
    return
  res = task(get_rooms_info_by_uids(uids, reqtype="web", proxies=proxy))
  open('test.txt','w', encoding='utf-8').write(str(res))
  if not res:
    return
  for uid, live in res.items():
    status = int(live["live_status"]) % 2
    if uid not in live_status:
      live_status[uid] = status
      continue
    if live_status[uid] == status:
      continue
    live_status[uid] = status

    if status:
      for owner_id in follow_list:
        if uid in follow_list[owner_id]:
          option = follow_list[owner_id][uid]
          if option['global_notice'] and option['live_notice'] and re.search(option['keyword'], live["title"]):
            room_id = live["short_id"] if live["short_id"] else live["room_id"]
            msg = f'{live["uname"]}开播啦~'
            msg += f'\n{live["title"]}'
            if cover:
              msg += f'\n[CQ:image,file={live["cover_from_user"]}]'
            msg += f'https://live.bilibili.com/{room_id}'
            msg += f'\n========近期画面========'
            msg += f'\n[CQ:image,file={live["keyframe"]}]'
            reply_back(owner_id, msg)
  time.sleep(10)

def dynamic_check(proxy=None):
  uids = get_uid_list("dynamic")
  if not uids:
    return
  for uid in uids:
    try:
      dynamic = get_new_dynamic(uid)
    except:
      warnf(f"[B站动态检测] 爬取动态超时,等待下一轮询重试~")
      continue

    if dynamic:
      name = dynamic[0]
      dynamic_id = dynamic[1]
      dynamic_type = dynamic[2]
      text = dynamic[3]
      for owner_id in follow_list:
        if uid in follow_list[owner_id]:
          info = follow_list[owner_id][uid]
          if info['global_notice'] and info['dynamic_notice'] and re.search(info['keyword'], text):
            type_msg = {0: "发布了新动态", 1: "转发了一条动态", 2: "发布了新投稿", 6: "发布了新图文动态", 7: "发布了新文字动态", 8: "发布了新专栏", 9: "发布了新音频"}
            name = get_name_by_uid(uid)
            if dynamic_type in type_msg: msg = f'{name}{type_msg[dynamic_type]}：'
            else : msg = f'{name}发布了新动态{dynamic_type}：'
            msg += f'\nhttps://t.bilibili.com/{dynamic_id}'
            msg += f'\n[CQ:image,file=bilibili/{dynamic_id}.png]'
            reply_back(owner_id, msg)
    time.sleep(3)

def fans_check(check_day=True,proxy=None):
  global today
  if check_day and today == time.gmtime().tm_yday:
    return
  uids = get_uid_list("fans")
  if not uids:
    return
  for uid in uids:
    try:
      info = get_user_info(uid)
    except:
      warnf(f"[B站动态检测] 爬取粉丝数超时,等待下一轮询重试~")
      continue

    if info:
      uid = info[0]
      name = info[1]
      fans = int(info[2])
      avatar = info[3]
      past_fans = int(get_follow_list_info(uid, 'fans'))
      if past_fans == fans:
        continue
      today = time.gmtime().tm_yday
      for owner_id in follow_list:
        if uid in follow_list[owner_id]:
          info = follow_list[owner_id][uid]
          if info['global_notice'] and info['fans_notice']:
            msg = f'\n[CQ:image,file={avatar}]'
            msg += f'{name}当前的粉丝数为：{fans}'
            diff = fans - past_fans
            if diff > 0:
              msg += f'\n相比上次记录，粉丝数增加了{diff}，'
              if diff > 10000 or diff > fans:
                msg += f'大跃进都没有{name}的涨粉浮夸！'
              elif diff > 1000 or (1000 < fans < 10000 and diff > fans/10):
                msg += f'成为百大指日可待~'
              elif diff > 100 or diff > fans/40:
                msg += f'很棒棒啦，继续加把劲~'
              elif diff > 10 or diff > fans/100:
                msg += f'继续加油哦~'
              else:
                msg += f'聊胜于无嘛(oﾟvﾟ)ノ'
            elif diff < 0:
              diff = abs(diff)
              msg += f'\n相比上次记录，粉丝数减少了了{diff}，'
              if diff > 10000 or diff > fans/2:
                msg += f'仿佛只在次贷危机看过类似的场景...'
              elif diff > 1000 or (fans > 10000 and diff > fans/10):
                msg += f'大危机！(っ °Д °;)っ'
              elif diff > 200 or (fans > 10000 and diff > fans/50):
                msg += f'哦吼，不太妙哦~(#｀-_ゝ-)'
              elif diff > 25 or diff > fans/100:
                msg += f'一点小失误...(￣﹃￣)'
              else:
                msg += f'，统计学上来说这很正常'
            else: continue
            update_follow_list_info(uid, {'fans': fans})
            reply_back(owner_id, msg)
    time.sleep(3)

def get_follow_list_info(input_uid, name):
  for owner_id in follow_list:
    for uid in follow_list[owner_id]:
      if uid == input_uid:
        return follow_list[owner_id][uid][name]
  return ''

def update_follow_list_info(input_uid, data):
  for key,value in data.items():
    for owner_id in follow_list:
      for uid in follow_list[owner_id]:
        if uid == input_uid:
          follow_list[owner_id][uid][key] = value
  save_json(data_file, follow_list)

def get_new_dynamic(uid,proxy=None):
  if uid not in past_dynamics:
    init_dynamic(uid)
    time.sleep(3)
  dynamics = task(grpc_get_user_dynamics(int(uid), timeout=10, proxy=proxy)).list
  if len(dynamics) > 0:
    dynamic_id = int(dynamics[0].extend.dyn_id_str)
    index = 0
    if len(dynamics) != 1:
      if int(dynamics[0].extend.dyn_id_str) < int(dynamics[1].extend.dyn_id_str):
        del dynamics[0]
      for i in range(len(dynamics)):
        if dynamics[i].extend.dyn_id_str not in past_dynamics[uid]:
          dynamic_id = int(dynamics[i].extend.dyn_id_str)
          index = i
          break
    dynamic_type = dynamics[index].card_type
    author_name = dynamics[index].modules[0].module_author.author.name
    text = dynamics[index].extend.orig_desc[0].text
    if str(dynamic_id) not in past_dynamics[uid]:
      past_dynamics[uid].append(str(dynamic_id))
      image = task(Browser.get_dynamic_screenshot(dynamic_id))
      image_file = f'{dynamic_id}.png'
      image_save(image_file, image)
      return [author_name, dynamic_id, dynamic_type, text]
  return None

def get_latest_dynamic(uid,proxy=None):
  dynamics = task(grpc_get_user_dynamics(int(uid), timeout=10, proxy=proxy)).list
  if len(dynamics) > 0:
    dynamic_id = int(dynamics[0].extend.dyn_id_str)
    index = 0
    if len(dynamics) != 1:
      if int(dynamics[0].extend.dyn_id_str) < int(dynamics[1].extend.dyn_id_str):
        del dynamics[0]
    index = 0
    dynamic_id = dynamics[index].extend.dyn_id_str
    dynamic_type = dynamics[index].card_type
    author_name = dynamics[index].modules[0].module_author.author.name
    text = dynamics[index].extend.orig_desc[0].text
    image = task(Browser.get_dynamic_screenshot(dynamic_id))
    image_file = f'{dynamic_id}.png'
    image_save(image_file, image)
    return [author_name, dynamic_id, dynamic_type, text]
  return None

def init_dynamic(uid,proxy=None):
  if uid not in past_dynamics:
    past_dynamics[uid] = []
  dynamics = task(grpc_get_user_dynamics(int(uid), timeout=10, proxy=proxy)).list
  if len(dynamics) > 0:
    for i in range(len(dynamics)):
      past_dynamics[uid].append(str(dynamics[i].extend.dyn_id_str))

def get_live_status(uid,proxy=None):
  info = task(get_rooms_info_by_uids([uid], reqtype="web", proxies=proxy))
  if info != []:
    data = info[uid]
    online = data['live_status']
    title = data['title']
    cover = data['cover_from_user']
    room_id = data["short_id"] if data["short_id"] else data["room_id"]
    time = data['live_time']
    num = data['online']
    frame = data['keyframe']
    if gVar.is_debug:
      warnf(f'[DATA] [{module_name}] [直播间信息] {str(info)}')
    return [online, title, cover, room_id, time, num, frame]
  else:
    return None

def get_user_info(uid):
  url = 'https://api.bilibili.com/x/web-interface/card?mid=' + str(uid)
  try: info = json.loads(requests.get(url).text)
  except:
    time.sleep(1)
    try: info = json.loads(requests.get(url).text)
    except: warnf('查询用户信息请求失败！')
  
  if 'data' in info and info['data']:
    name = str(info['data']['card']['name'])
    fans = str(info['data']['card']['fans'])
    avatar = str(info['data']['card']['face'])
    return [uid,name,fans,avatar]
  else:
    return None

def get_uid(user):
  for owner_id in follow_list:
    for uid in follow_list[owner_id]:
      if user == follow_list[owner_id][uid]['name'] or user == follow_list[owner_id][uid]['label']:
        return uid
  if re.search(r'^[0-9]+$',user):
    return user
  return None

def get_name_by_uid(check_uid):
  for owner_id in follow_list:
    for uid in follow_list[owner_id]:
      if check_uid == uid:
        return follow_list[owner_id][uid]['name']
  return None

def get_info_by_name(name):
  url = f'https://api.bilibili.com/x/web-interface/search/type?&page=1&order=fans&order_sort=0&search_type=bili_user&keyword={name}'
  referer = 'https://search.bilibili.com/upuser&order=fans&user_type=1&order_sort=0&search_type=bili_user'
  agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
  cookies = "b_lsid=E6F85982_184136B1015; _uuid=7E10ACE68-3397-12C9-EB37-B1D921022A92F94432infoc; buvid_fp=2f6322af55142c1aba54cbbba6b46100; buvid3=E17B6733-DFE2-7880-82B9-908960A59EBF95886infoc; b_nut=1666773095; buvid4=6A0D5814-5124-7764-A5E0-D19709AB8CE695886-022102616-XGa5iM2WFJKxaEoQ/jft0A%3D%3D; nostalgia_conf=-1; PVID=1"
  
  try: resp = requests.get(url, headers={"referer": referer, "user-agent": agent, "cookie": cookies})
  except:
    time.sleep(1)
    try: resp = requests.get(url, headers={"referer": referer, "user-agent": agent, "cookie": cookies})
    except: warnf('查询用户信息请求失败！')

  info = json.loads(resp.text)
  if info['data'] and 'result' in info['data']:
    for result in info['data']['result']:
      if result['type'] == 'bili_user':
        uid = str(result['mid'])
        name = result['uname']
        fans = result['fans']
        avatar = 'https:' + result['upic']
        break
    return [uid, name, fans, avatar]
  else:
    return None

def get_info(user):
  uid = get_uid(user)
  info = None
  if uid:
    info = get_user_info(uid)
  if not info:
    info = get_info_by_name(user)
    if not info:
      return None
  if gVar.is_debug:
    warnf(f'[DATA] [{module_name}] [用户信息] {str(info)}')
  update_follow_list_info(uid, {'name': info[1], 'fans': info[2], 'avatar': info[3]})
  return info

def get_uid_list(get_type=None):
  uid_list = []
  for owner_id in follow_list:
    for uid in follow_list[owner_id]:
      if follow_list[owner_id][uid]['global_notice']:
        if get_type == 'dynamic' and follow_list[owner_id][uid]['dynamic_notice'] == True:
          uid_list.append(uid)
        elif get_type == 'live' and follow_list[owner_id][uid]['live_notice'] == True:
          uid_list.append(uid)
        elif get_type == 'fans' and follow_list[owner_id][uid]['fans_notice'] == True:
          uid_list.append(uid)
  return uid_list

def print_user_data(uid, one_follow_list):
  if uid in one_follow_list:
    info = f'\n[CQ:image,file={one_follow_list[uid]["avatar"]},subType=1]'
    info += f'\n用户名：{one_follow_list[uid]["name"]}'
    info += f'\n昵称：{one_follow_list[uid]["label"]}'
    info += f'\nUID：{uid}'
    info += f'\n粉丝数：{one_follow_list[uid]["fans"]}'
    keyword = one_follow_list[uid]["keyword"] if one_follow_list[uid]["keyword"] != "" else "无(全部通知)"
    info += f'\n通知关键词：{keyword}'
    dynamic = "开启" if one_follow_list[uid]["dynamic_notice"] == True else "关闭"
    info += f'\n动态通知：{dynamic}'
    live = "开启" if one_follow_list[uid]["live_notice"] == True else "关闭"
    info += f'\n直播通知：{live}'
    live = "开启" if one_follow_list[uid]["fans_notice"] == True else "关闭"
    info += f'\n粉丝数通知：{live}'
    live = "开启" if one_follow_list[uid]["global_notice"] == True else "关闭"
    info += f'\n全局通知：{live}'
    return info
  else:
    return None

def follow_list_save(owner_id, one_follow_list):
  follow_list[owner_id] = one_follow_list
  save_json(data_file, follow_list)

def image_save(file_name,file):
  image_dir = gVar.data_dir + '/images'
  if not os.path.exists(image_dir):
    raise RuntimeError('CQHttp数据文件夹设置不正确！')
  if not os.path.exists(f'{image_dir}/bilibili'):
    os.mkdir(f'{image_dir}/bilibili')
  open(f'{image_dir}/bilibili/{file_name}', mode="wb").write(file)
  return f'{image_dir}/bilibili/{file_name}'

def task(task_func):
  task = loop.create_task(task_func)
  loop.run_until_complete(task)
  return task.result()

def bilibili_loop():
  time.sleep(10)
  warnf(f'[{module_name}] 实时检测开启~')
  while True:
    dynamic_check()
    fans_check()
    live_check()

def fans_check_loop(uid, owner_id):
  global bilibili_thread_running
  bilibili_thread_running = True
  time.sleep(1)
  past_fans = int(get_info(uid)[2])
  while bilibili_thread_running:
    info = get_info(uid)
    if info:
      name = info[1]
      fans = int(info[2])
      msg = f'{name}当前的粉丝数为：{fans}'
      diff = fans - past_fans
      if diff > 10:
        msg += f'\n相比上次增加了{diff}'
        reply_back(owner_id, msg)
        past_fans = fans
      elif diff < -10:
        msg += f'\n相比上次减少了{abs(diff)}'
        reply_back(owner_id, msg)
        past_fans = fans
    else:
      msg = f"获取粉丝数失败,等待下一轮询重试~"
      reply_back(owner_id, msg)
    time.sleep(10)

threading.Thread(target=bilibili_loop, daemon=True).start()
Browser = browser()



module_enable(module_name, bilibili)