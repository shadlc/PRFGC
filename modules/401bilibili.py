"""哔哩哔哩模块"""

import asyncio
import base64
import re
import threading
import time
import traceback

from bilibili_api.user import User
from bilibili_api.live import LiveRoom
from bilibili_api.exceptions import ResponseCodeException

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from src.utils import Module, via

class Bilibili(Module):
    """哔哩哔哩模块"""

    ID = "Bilibili"
    NAME = "哔哩哔哩模块"
    HELP = {
        3: [
            "关注列表 | 查看当前关注的UP主列表",
            "[UP主] 动态 | 获取UP主的最新动态",
            "[UP主] 直播 | 获取UP主的直播间状态",
            "[UP主] 粉丝数 | 查看该UP粉丝数",
            "[UP主] 动态 [开启|关闭] | 开关UP主动态通知",
            "[UP主] 直播 [开启|关闭] | 开关UP主直播通知",
            "[UP主] 粉丝数 [开启|关闭] | 开关UP主粉丝数通知",
            "关注 [UP主] | 关注一个新的UP主",
            "取关 [UP主] | 取关一个UP主",
            "通知关键词 [UP主] [匹配规则] | 设置通知过滤关键词(正则匹配)",
            "[UP主] 通知 [开启|关闭] | 开关UP主的通知",
        ],
    }
    CONFIG = "bilibili.json"
    GLOBAL_CONFIG = {
        "sessdata": "",
        "bili_jct": "",
        "buvid3": "",
        "user_agent": "",
    }
    CONV_CONFIG = {
        "sub": {},
        "browser": {
            "proxy": None
        }
    }

    def __init__(self, event, auth=0):
        super().__init__(event, auth)
        if hasattr(self.robot, "bilibili"):
            return
        self.robot.bilibili = self
        self.live_status = {}
        self.past_dynamics = {}
        self.new_dynamics = {}
        self.deleted_dynamic_list = {}
        self.today = time.gmtime().tm_yday
        self.browser = None
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_loop, daemon=True).start()
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def monitor_loop(self):
        time.sleep(10)
        self.printf("实时检测开启~")
        while True:
            self.dynamic_check()
            self.fans_check()
            self.live_check()
            time.sleep(60)

    @via(lambda self: self.at_or_private() and self.au(3) and self.match(r"^关注列表$"))
    def show_follow_list(self):
        """显示关注列表"""
        follow_list = self.config[self.owner_id]["sub"]
        if follow_list:
            if self.event.group_id:
                msg = "本群的关注列表"
            else:
                msg = "你的关注列表"
            for uid, info in follow_list.items():
                user_info = self.get_user_info(uid)
                if user_info:
                    info["name"] = user_info[1]
                    info["fans"] = user_info[2]
                    info["avatar"] = user_info[3]
                msg += "\n===================="
                msg += self._print_user_data(uid, info)
            self.save_config()
        else:
            msg = "这里还未拥有关注列表，请管理员添加吧~"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^关注\s?(\S+)$"))
    def subscribe(self):
        """关注UP主"""
        user_input = self.match(r"^关注\s?(\S+)$").groups()[0]
        info = self.get_info(user_input)
        if info:
            uid, name, fans, avatar = info
            if uid in self.config[self.owner_id]["sub"]:
                msg = f"你已经关注了{self.config[self.owner_id]['sub'][uid]['name']}"
            else:
                self.config[self.owner_id]["sub"][uid] = {
                    "name": name,
                    "avatar": avatar,
                    "fans": fans,
                    "keyword": "",
                    "dynamic_notice": True,
                    "live_notice": True,
                    "fans_notice": False,
                    "global_notice": True
                }
                self.save_config()
                msg = f"已将{name}(UID:{uid})添加至关注列表"
            msg += "\n===================="
            msg += self._print_user_data(uid, self.config[self.owner_id]["sub"][uid])
        else:
            msg = "查无此人"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^取关\s?(\S+)$"))
    def unsubscribe(self):
        """取关UP主"""
        user_input = self.match(r"^取关\s?(\S+)$").groups()[0]
        info = self.get_info(user_input)
        if info:
            uid, name = info[0], info[1]
            if uid not in self.config[self.owner_id]["sub"]:
                msg = f"你并没有关注{name}"
            else:
                msg = f"已将{name}(UID:{uid})取关"
                del self.config[self.owner_id]["sub"][uid]
                self.save_config()
        else:
            msg = "查无此人"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^通知关键词\s?(\S+)\s+(\S+)$"))
    def set_keywords(self):
        """设置通知关键词"""
        user_input, pattern = self.match(r"^通知关键词\s?(\S+)\s+(\S+)$").groups()
        info = self.get_info(user_input)
        if info:
            uid, name = info[0], info[1]
            if uid in self.config[self.owner_id]["sub"]:
                self.config[self.owner_id]["sub"][uid]["keyword"] = pattern
                self.save_config()
                msg = f"已成功为{name}设置正则匹配关键词【{pattern}】"
            else:
                msg = "未关注该UP主，请先关注！"
        else:
            msg = "查无此人"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(3) and self.match(r"^(\S+)\s?动态\s?(开启|关闭)?$"))
    def dynamic_control(self):
        """动态控制"""
        user_input, flag = self.match(r"^(\S+)\s?动态\s?(开启|关闭)?$").groups()
        info = self.get_info(user_input)
        if info:
            uid, name = info[0], info[1]
            if not flag:
                dynamic = self.get_latest_dynamic(uid)
                if dynamic:
                    name, dynamic_id, _, content = dynamic
                    msg = f"{name}的最新一条动态："
                    msg += f"\nhttps://t.bilibili.com/{dynamic_id}"
                    if not HAS_PLAYWRIGHT:
                        msg += f"\n{content}"
                    else:
                        screenshot_base64 = self.run_async(self.get_dynamic_screenshot(dynamic_id))
                        if screenshot_base64:
                            msg += f"\n[CQ:image,file=base64://{screenshot_base64}]"
                        else:
                            msg += f"\n{content}"
                else:
                    msg = f"{name}没有发过任何动态..."
            elif uid in self.config[self.owner_id]["sub"]:
                status = flag == "开启"
                self.config[self.owner_id]["sub"][uid]["dynamic_notice"] = status
                self.save_config()
                msg = f"已{'开启' if status else '关闭'}对{name}的动态观测~"
            else:
                msg = "请先关注UP主~"
        else:
            msg = "查无此人"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(3) and self.match(r"^(\S+)\s?直播\s?(开启|关闭)?$"))
    def live_control(self):
        """直播控制"""
        user_input, flag = self.match(r"^(\S+)\s?直播\s?(开启|关闭)?$").groups()
        info = self.get_info(user_input)
        if info:
            uid, name = info[0], info[1]
            if not flag:
                status = self.get_live_status(uid)
                if status:
                    online, title, cover, room_id, live_time, online_num, keyframe = status
                    if online:
                        msg = f"{name}正在直播："
                        msg += f"\n{title}"
                        if cover:
                            msg += f"\n[CQ:image,file={cover}]"
                        msg += f"\nhttps://live.bilibili.com/{room_id}"
                        msg += f"\n已经直播了{time.strftime('%H小时%M分钟', time.gmtime(time.time() - int(live_time)))}，{online_num}人在看"
                        if keyframe:
                            msg += f"\n========近期画面========"
                            msg += f"\n[CQ:image,file={keyframe}]"
                    else:
                        msg = f"{name}在休息中哦~"
                else:
                    msg = f"{name}从来没有直播过哦~"
            elif uid in self.config[self.owner_id]["sub"]:
                status = flag == "开启"
                self.config[self.owner_id]["sub"][uid]["live_notice"] = status
                self.save_config()
                msg = f"已{'开启' if status else '关闭'}对{name}的直播通知~"
            else:
                msg = "请先关注UP主~"
        else:
            msg = "查无此人"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(3) and self.match(r"^(\S+)\s?粉丝数\s?(开启|关闭)?$"))
    def fans_control(self):
        """粉丝数控制"""
        user_input, flag = self.match(r"^(\S+)\s?粉丝数\s?(开启|关闭)?$").groups()
        info = self.get_info(user_input)
        if info:
            uid, name, fans, avatar = info
            if not flag:
                msg = f"{name}当前的粉丝数为：{fans}"
                msg += f"\n[CQ:image,file={avatar}]"
            elif uid in self.config[self.owner_id]["sub"]:
                status = flag == "开启"
                self.config[self.owner_id]["sub"][uid]["fans_notice"] = status
                self.save_config()
                msg = f"已{'开启' if status else '关闭'}对{name}的粉丝数通知~"
            else:
                msg = "请先关注UP主~"
        else:
            msg = "查无此人"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^(\S+)\s?通知\s?(开启|关闭)$"))
    def notice_control(self):
        """通知控制"""
        user_input, flag = self.match(r"^(\S+)\s?通知\s?(开启|关闭)$").groups()
        if user_input == "全部":
            status = flag == "开启"
            for uid in self.config[self.owner_id]["sub"]:
                self.config[self.owner_id]["sub"][uid]["global_notice"] = status
            self.save_config()
            msg = f"已{flag}全体UP主的通知~"
        else:
            info = self.get_info(user_input)
            if info:
                uid, name = info[0], info[1]
                if uid in self.config[self.owner_id]["sub"]:
                    status = flag == "开启"
                    self.config[self.owner_id]["sub"][uid]["global_notice"] = status
                    self.save_config()
                    msg = f"已{flag}对{name}的全部通知~"
                else:
                    msg = "请先关注UP主~"
            else:
                msg = "查无此人"
        self.reply(msg)

    async def init_browser(self):
        """初始化浏览器"""
        if self.browser:
            return self.browser

        if not HAS_PLAYWRIGHT:
            return None

        p = await async_playwright().start()
        browser_config = self.config["browser"].copy()
        proxy = browser_config.pop("proxy", None)
        if proxy:
            browser_config["proxy"] = {"server": proxy}

        self.browser = await p.chromium.launch(**browser_config)
        return self.browser

    async def get_dynamic_screenshot(self, dynamic_id, style="mobile"):
        """获取动态截图并返回base64"""
        if not HAS_PLAYWRIGHT:
            return None
            
        if style.lower() == "mobile":
            return await self.get_dynamic_screenshot_mobile(dynamic_id)
        else:
            return await self.get_dynamic_screenshot_pc(dynamic_id)

    async def get_dynamic_screenshot_mobile(self, dynamic_id):
        """移动端动态截图"""
        url = f"https://m.bilibili.com/dynamic/{dynamic_id}"
        browser = await self.init_browser()
        if not browser:
            return None
            
        context = await browser.new_context(
            device_scale_factor=2,
            user_agent=self.config["user_agent"],
            viewport={"width": 500, "height": 800},
        )

        await context.add_cookies([
            {
                "name": "SESSDATA",
                "value": self.config["sessdata"],
                "domain": ".bilibili.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            }
        ])

        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=10000)
            if page.url == "https://m.bilibili.com/404":
                return None

            await page.add_script_tag(content="""
                document.querySelectorAll('.opus-float-btn').forEach(v=>v.remove());
                document.querySelectorAll('.dynamic-float-btn').forEach(v=>v.remove());
                document.querySelectorAll('.dyn-header__following').forEach(v=>v.remove());
                document.querySelectorAll('.dyn-share').forEach(v=>v.remove());

                const contentDiv = document.getElementsByClassName('dyn-card')[0];
                const wrapperDiv = document.createElement('div');
                contentDiv.parentNode.insertBefore(wrapperDiv, contentDiv);
                wrapperDiv.appendChild(contentDiv);

                wrapperDiv.style.padding = '10px';
                wrapperDiv.style.backgroundImage = 'linear-gradient(to bottom right, #c8beff, #bef5ff)';
                contentDiv.style.boxShadow = '0px 0px 10px 2px #fff';
                contentDiv.style.border = '2px solid white';
                contentDiv.style.borderRadius = '10px';
                contentDiv.style.background = 'rgba(255,255,255,0.7)';
                contentDiv.style.fontFamily = 'Noto Sans CJK SC, sans-serif';
                contentDiv.style.overflowWrap = 'break-word';

                document.getElementsByClassName('dyn-content__orig')[0].style.backgroundColor = 'transparent';
                document.querySelectorAll('img').forEach(v=>{ v.style.border = '2px solid white'; });
                document.getElementsByClassName('dyn-article__card').forEach(v=>{ v.style.border = '2px solid white'; v.style.background = 'transparent'; });
                document.querySelectorAll('[class*="pair--"]>*').forEach((e)=>{e.style.width="42.9vmin";e.style.height="42.9vmin";});
                document.querySelectorAll('[class*="well--"]>*').forEach((e)=>{e.style.width="28vmin";e.style.height="28vmin";});
            """)

            card = await page.query_selector(".card-wrap")
            if card:
                clip = await card.bounding_box()
                if clip:
                    screenshot = await page.screenshot(clip=clip, full_page=True)
                    return base64.b64encode(screenshot).decode('utf-8')
        except Exception as e:
            self.errorf(f"截取动态【{url}】时发生错误：{traceback.format_exc()}")
        finally:
            await page.close()
            await context.close()
        return None

    async def get_dynamic_screenshot_pc(self, dynamic_id):
        """电脑端动态截图"""
        url = f"https://t.bilibili.com/{dynamic_id}"
        browser = await self.init_browser()
        if not browser:
            return None
            
        context = await browser.new_context(
            viewport={"width": 2560, "height": 1080},
            device_scale_factor=2,
        )

        await context.add_cookies([
            {
                "name": "SESSDATA",
                "value": self.config["sessdata"],
                "domain": ".bilibili.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            }
        ])

        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=10000)
            if page.url == "https://www.bilibili.com/404":
                return None

            card = await page.query_selector(".card")
            if card:
                clip = await card.bounding_box()
                if clip:
                    bar = await page.query_selector(".bili-dyn-action__icon")
                    if bar:
                        bar_bound = await bar.bounding_box()
                        if bar_bound:
                            clip["height"] = bar_bound["y"] - clip["y"]
                    screenshot = await page.screenshot(clip=clip, full_page=True)
                    return base64.b64encode(screenshot).decode('utf-8')
        except Exception as e:
            self.errorf(f"截取动态【{url}】时发生错误：{traceback.format_exc()}")
        finally:
            await context.close()
        return None

    def live_check(self):
        """直播检查"""
        uids = self.get_uid_list("live")
        if not uids:
            return

        try:
            for uid in uids:
                room_info = self.run_async(LiveRoom(uid).get_room_info())
                if room_info:
                    status = 1 if room_info['live_status'] == 1 else 0
                    if uid not in self.live_status:
                        self.live_status[uid] = status
                        continue

                    if self.live_status[uid] == status:
                        continue

                    self.live_status[uid] = status
                    if status:
                        for owner_id in self.config:
                            if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                                continue

                            if uid in self.config[owner_id]["sub"]:
                                option = self.config[owner_id]["sub"][uid]
                                if (option["global_notice"] and option["live_notice"] and 
                                    re.search(option["keyword"], room_info["title"])):
                                    room_id = room_info["room_id"]
                                    msg = f'{room_info["uname"]}开播啦~'
                                    msg += f'\n{room_info["title"]}'
                                    if room_info["cover"]:
                                        msg += f'\n[CQ:image,file={room_info["cover"]}]'
                                    msg += f'https://live.bilibili.com/{room_id}'
                                    if room_info["keyframe"]:
                                        msg += f'\n========上次直播画面========'
                                        msg += f'\n[CQ:image,file={room_info["keyframe"]}]'
                                    self.reply_back(owner_id, msg)
        except Exception as e:
            self.warnf(f"爬取直播状态超时: {e}")
            time.sleep(10)

    def dynamic_check(self):
        """动态检查"""
        uids = self.get_uid_list("dynamic")
        if not uids:
            return

        for uid in uids:
            try:
                if not self.refresh_dynamics(uid):
                    self.warnf("冷却60秒~")
                    time.sleep(60)
            except Exception as e:
                self.warnf(f"爬取动态超时({e}),等待下一轮询重试~")
                time.sleep(30)
                return

            time.sleep(10)
            type_msg = {
                0: "发布了新动态", 
                1: "转发了一条动态", 
                2: "发布了新投稿", 
                6: "发布了新图文动态", 
                7: "发布了新文字动态", 
                8: "发布了新专栏", 
                9: "发布了新音频"
            }

            dynamics = self.get_new_dynamics(uid)
            for dynamic in dynamics:
                dynamic_id = dynamic["dynamic_id"]
                author = dynamic["author"]
                dynamic_type = dynamic["dynamic_type"]
                content = dynamic["content"]

                for owner_id in self.config:
                    if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                        continue

                    if uid in self.config[owner_id]["sub"]:
                        info = self.config[owner_id]["sub"][uid]
                        if (info["global_notice"] and info["dynamic_notice"] and 
                            re.search(info["keyword"], content)):
                            author = self.get_name_by_uid(uid)
                            if dynamic_type in type_msg:
                                msg = f'{author}{type_msg[dynamic_type]}：'
                            else:
                                msg = f'{author}发布了新动态{dynamic_type}：'

                            msg += f'\nhttps://t.bilibili.com/{dynamic_id}'
                            if not HAS_PLAYWRIGHT:
                                msg += f"\n{content}"
                            else:
                                screenshot_base64 = self.run_async(self.get_dynamic_screenshot(dynamic_id))
                                if screenshot_base64:
                                    msg += f'\n[CQ:image,file=base64://{screenshot_base64}]'
                                else:
                                    msg += f"\n{content}"

                            self.reply_back(owner_id, msg)
                            time.sleep(5)

            dynamics = self.get_deleted_dynamic(uid)
            if not dynamics or uid not in self.deleted_dynamic_list:
                self.deleted_dynamic_list[uid] = []

            self.deleted_dynamic_list[uid] += dynamics
            max_count = 0
            for item in self.deleted_dynamic_list[uid]:
                if (count := self.deleted_dynamic_list[uid].count(item)) > max_count:
                    max_count = count

            if max_count < 5:
                continue

            for dynamic in dynamics:
                dynamic_id = dynamic["dynamic_id"]
                author = dynamic["author"]
                dynamic_type = dynamic["dynamic_type"]
                content = dynamic["content"]

                for owner_id in self.config:
                    if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                        continue

                    if uid in self.config[owner_id]["sub"]:
                        info = self.config[owner_id]["sub"][uid]
                        if (info["global_notice"] and info["dynamic_notice"] and 
                            re.search(info["keyword"], content)):
                            author = self.get_name_by_uid(uid)
                            msg = ""
                            if not HAS_PLAYWRIGHT:
                                msg = f'{author}删除了一条动态~但我没有来得及保存截图~嘤嘤嘤~'
                                msg += f'\n\n动态内容：\n{content}'
                                msg += f'\n\n动态旧地址：https://t.bilibili.com/{dynamic_id}'
                            else:
                                msg = f'{author}已将此动态删除啦~'
                                # 尝试获取已保存的截图
                                screenshot_base64 = self.run_async(self.get_dynamic_screenshot(dynamic_id))
                                if screenshot_base64:
                                    msg += f'\n[CQ:image,file=base64://{screenshot_base64}]'
                                else:
                                    msg += f"\n{content}"

                            if dynamic in self.past_dynamics[uid]:
                                self.past_dynamics[uid].remove(dynamic)
                                self.deleted_dynamic_list[uid] = [x for x in self.deleted_dynamic_list[uid] if x != dynamic]

                            self.reply_back(owner_id, msg)
                            time.sleep(5)

    def fans_check(self, check_day=True):
        """粉丝数检查"""
        if check_day and self.today == time.gmtime().tm_yday:
            return

        uids = self.get_uid_list("fans")
        if not uids:
            return

        for uid in uids:
            try:
                info = self.get_user_info(uid)
            except Exception as e:
                self.warnf(f"爬取粉丝数超时: {e}")
                time.sleep(2)
                continue

            if info:
                uid, name, fans, avatar = info
                past_fans = int(self.get_follow_list_info(uid, "fans"))
                if past_fans == fans:
                    continue

                self.today = time.gmtime().tm_yday
                for owner_id in self.config:
                    if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                        continue

                    if uid in self.config[owner_id]["sub"]:
                        info = self.config[owner_id]["sub"][uid]
                        if info["global_notice"] and info["fans_notice"]:
                            msg = f'\n[CQ:image,file={avatar}]'
                            msg += f'{name}当前的粉丝数为：{fans}'
                            diff = fans - past_fans

                            if hasattr(self.robot, "get_chatgpt"):
                                if diff > 0:
                                    msg += f'\n相比上次记录，粉丝数增加了{diff}'
                                else:
                                    msg += f'\n相比上次记录，粉丝数减少了了{abs(diff)}'

                                date = time.strftime("%Y年%m月%d日", time.localtime())
                                prompt = f'今天是{date}，账号《{name}》从原来的粉丝数量{past_fans}变化为{fans}个，请用简短的两句话，表达自己的看法，请多夹杂日式颜文字和可爱的语气来说明，并使用括号描述自己的动作与心情，如果明白，请直接回复内容'
                                msg += '\n' + self.robot.get_chatgpt(prompt)
                            elif diff > 0:
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
                                    msg += f'统计学上来说这很正常'
                            else:
                                continue

                            self.update_follow_list_info(uid, {"fans": fans})
                            self.reply_back(owner_id, msg)
            time.sleep(2)

    def get_follow_list_info(self, uid, key):
        """获取关注列表信息"""
        for owner_id in self.config:
            if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                continue

            if uid in self.config[owner_id]["sub"]:
                return self.config[owner_id]["sub"][uid].get(key, "")
        return ""

    def update_follow_list_info(self, uid, data):
        """更新关注列表信息"""
        for key, value in data.items():
            for owner_id in self.config:
                if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                    continue

                if uid in self.config[owner_id]["sub"]:
                    self.config[owner_id]["sub"][uid][key] = value

        self.save_config()

    def refresh_dynamics(self, uid):
        """刷新动态"""
        try:
            u = user.User(int(uid))
            dynamics = self.run_async(u.get_dynamics())
            dynamic_list = dynamics.get("items", [])
        except Exception as e:
            self.warnf(f"用户{uid}的动态获取失败: {e}")
            dynamic_list = []

        if isinstance(dynamic_list, str):
            self.warnf(dynamic_list)
            return False

        if dynamic_list:
            dynamics = []
            for dynamic_json in dynamic_list:
                if dynamic_json.get("modules", {}).get("module_tag", {}).get("text") == "置顶":
                    continue

                if uid not in self.new_dynamics:
                    self.new_dynamics[uid] = []

                dynamic_type = dynamic_json.get("type")
                modules = dynamic_json.get("modules", {})
                module_dynamic = modules.get("module_dynamic", {})
                
                # 获取动态内容
                content = ""
                if module_dynamic.get("major", {}).get("opus"):
                    content = module_dynamic["major"]["opus"].get("summary", {}).get("text", "")
                elif module_dynamic.get("major", {}).get("article"):
                    content = module_dynamic["major"]["article"].get("title", "")
                elif module_dynamic.get("major", {}).get("none"):
                    content = module_dynamic["major"]["none"].get("content", "")
                
                # 获取作者信息
                author = modules.get("module_author", {}).get("name", "")

                dynamics.append({
                    "dynamic_id": dynamic_json["id_str"],
                    "author": author,
                    "dynamic_type": dynamic_type,
                    "content": content
                })

            self.new_dynamics[uid] = dynamics
            if uid not in self.past_dynamics:
                self.past_dynamics[uid] = self.new_dynamics[uid].copy()

            return True
        return False

    def get_new_dynamics(self, uid):
        """获取新动态"""
        dynamics = self.new_dynamics.get(uid, [])
        result = []

        if dynamics:
            for i in range(len(dynamics)):
                dynamic_id = dynamics[i]["dynamic_id"]
                if (dynamic_id not in [d["dynamic_id"] for d in self.past_dynamics.get(uid, [])] and 
                    int(dynamic_id) >= int(self.past_dynamics[uid][-1]["dynamic_id"])):

                    self.past_dynamics[uid].insert(i, dynamics[i])
                    if HAS_PLAYWRIGHT:
                        self.run_async(self.get_dynamic_screenshot(dynamic_id))

                    result.append(dynamics[i])

        return result

    def get_deleted_dynamic(self, uid):
        """获取删除的动态"""
        result = []
        if uid not in self.past_dynamics or uid not in self.new_dynamics:
            return result

        if not self.past_dynamics[uid] or not self.new_dynamics[uid]:
            return result

        for dynamic in self.past_dynamics[uid]:
            dynamic_id = dynamic["dynamic_id"]
            if (dynamic_id not in [d["dynamic_id"] for d in self.new_dynamics[uid]] and 
                int(dynamic_id) >= int(self.new_dynamics[uid][-1]["dynamic_id"])):

                result.append(dynamic)

        return result

    def get_latest_dynamic(self, uid):
        """获取最新动态"""
        if uid not in self.new_dynamics or not self.new_dynamics[uid]:
            self.refresh_dynamics(uid)

        dynamics = self.new_dynamics.get(uid, [])
        if dynamics:
            if len(dynamics) != 1:
                if int(dynamics[0]["dynamic_id"]) < int(dynamics[1]["dynamic_id"]):
                    dynamics.pop(0)

            dynamic_id = dynamics[0]["dynamic_id"]
            dynamic_type = dynamics[0]["dynamic_type"]
            author = dynamics[0]["author"]
            content = dynamics[0]["content"]

            if HAS_PLAYWRIGHT:
                self.run_async(self.get_dynamic_screenshot(dynamic_id))

            return [author, dynamic_id, dynamic_type, content]

        return None

    def get_live_status(self, uid):
        """获取直播状态"""
        try:
            room_info = self.run_async(LiveRoom(uid).get_room_info())
        except Exception as e:
            self.warnf(f"获取直播状态失败: {e}")
            room_info = None

        if room_info:
            online = room_info['live_status'] == 1
            title = room_info['title']
            cover = room_info['cover']
            room_id = room_info['room_id']
            live_time = room_info['live_time']
            online_num = room_info['online']
            keyframe = room_info['keyframe']

            return [online, title, cover, room_id, live_time, online_num, keyframe]

        return None

    def get_user_info(self, uid):
        """获取用户信息"""
        try:
            u = user.User(int(uid))
            info = self.run_async(u.get_user_info())
        except ResponseCodeException as e:
            self.warnf(f"查询用户信息请求失败: {e}")
            time.sleep(1)
            try:
                info = self.run_async(u.get_user_info())
            except Exception as e:
                self.warnf(f"查询用户信息请求失败: {e}")
                return None
        except Exception as e:
            self.warnf(f"查询用户信息请求失败: {e}")
            return None

        if info:
            name = str(info["name"])
            fans = str(info["follower"])
            avatar = str(info["face"])
            return [uid, name, fans, avatar]

        return None

    def get_uid(self, user_input):
        """获取用户UID"""
        for owner_id in self.config:
            if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                continue

            for uid, info in self.config[owner_id]["sub"].items():
                if user_input == info["name"]:
                    return uid

        if re.search(r"^[0-9]+$", user_input):
            return user_input

        return None

    def get_name_by_uid(self, uid):
        """通过UID获取用户名"""
        for owner_id in self.config:
            if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                continue

            if uid in self.config[owner_id]["sub"]:
                return self.config[owner_id]["sub"][uid]["name"]

        return None

    def get_info_by_name(self, name):
        """通过名称获取信息"""
        try:
            search_result = self.run_async(User.get_uid())
            if search_result and "result" in search_result:
                for result in search_result["result"]:
                    if result.get("uname") == name:
                        uid = str(result["mid"])
                        name = result["uname"]
                        fans = str(result["fans"])
                        avatar = result["upic"]
                        return [uid, name, fans, avatar]
        except Exception as e:
            self.warnf(f"查询用户信息请求失败: {e}")
            return None

        return None

    def get_info(self, user_input):
        """获取用户信息"""
        uid = self.get_uid(user_input)
        info = None

        if uid:
            info = self.get_user_info(uid)

        if info:
            self.update_follow_list_info(uid, {
                "name": info[1], 
                "fans": info[2], 
                "avatar": info[3]
            })
        else:
            info = self.get_info_by_name(user_input)
            if info:
                uid = info[0]
                self.update_follow_list_info(uid, {
                    "name": info[1], 
                    "fans": info[2], 
                    "avatar": info[3]
                })
            else:
                return None

        return info

    def get_uid_list(self, get_type=None):
        """获取UID列表"""
        uid_list = []
        for owner_id in self.config:
            if owner_id == "base_path" or owner_id == "data_file" or owner_id == "sessdata" or owner_id == "user_agent" or owner_id == "browser":
                continue

            for uid, info in self.config[owner_id]["sub"].items():
                if info["global_notice"]:
                    if get_type == "dynamic" and info["dynamic_notice"]:
                        uid_list.append(uid)
                    elif get_type == "live" and info["live_notice"]:
                        uid_list.append(uid)
                    elif get_type == "fans" and info["fans_notice"]:
                        uid_list.append(uid)

        return uid_list

    def _print_user_data(self, uid, info):
        """打印用户数据"""
        result = f"\n[CQ:image,file={info['avatar']},subType=1]"
        result += f"\n用户名：{info['name']}"
        result += f"\nUID：{uid}"
        result += f"\n粉丝数：{info['fans']}"
        keyword = info["keyword"] if info["keyword"] != "" else "无(全部通知)"
        result += f"\n通知关键词：{keyword}"
        dynamic = "开启" if info["dynamic_notice"] else "关闭"
        result += f"\n动态通知：{dynamic}"
        live = "开启" if info["live_notice"] else "关闭"
        result += f"\n直播通知：{live}"
        fans = "开启" if info["fans_notice"] else "关闭"
        result += f"\n粉丝数通知：{fans}"
        global_notice = "开启" if info["global_notice"] else "关闭"
        result += f"\n全局通知：{global_notice}"
        return result

    def run_async(self, coroutine):
        """运行异步函数"""
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        return future.result()

    def reply_back(self, owner_id, msg):
        """回复消息"""
        if owner_id.startswith("g"):
            group_id = int(owner_id[1:])
            self.robot.send_group_msg(group_id=group_id, message=msg)
        else:
            user_id = int(owner_id[1:])
            self.robot.send_private_msg(user_id=user_id, message=msg)