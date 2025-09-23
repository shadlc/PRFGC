"""图片处理模块"""

import asyncio
import base64
import io
import json
import random
import re
import time
import traceback
from typing import Any, Callable, Tuple
from urllib.parse import quote

import httpx
from PIL import Image

from src.utils import MiniCron, Module, build_node, calc_time, reply_back, set_emoji, via

class Picture(Module):
    """图片处理模块"""
    ID = "Picture"
    NAME = "图片处理模块"
    HELP = {
        2: [
            "打分 | 对图片色气度进行打分",
            "saucenao [图片] | 使用SauceNAO搜索图片",
            "来张色图 | 调用Lolicon API获取图片",
            "清晰术 | 调用Real-CUGAN增强图片清晰度"
        ],
    }
    GLOBAL_CONFIG = {
        "real_cugan_url": "",
        "saucenao_key": "",
        "serpapi_key": "",
    }
    CONV_CONFIG = {
        "animate_search": True,
        "image_search": True,
        "saucenao": True,
        "enhance": True,
        "jiandan": {
            "hist": [],
            "cron": "",
            "probability": 0.5,
        },
    }
    AUTO_INIT = True

    def __init__(self, event, auth = 0):
        super().__init__(event, auth)
        if self.ID in self.robot.persist_mods:
            return
        self.robot.persist_mods[self.ID] = self
        asyncio.run_coroutine_threadsafe(self.init_task(), self.robot.loop)

    async def init_task(self) -> None:
        """初始化定时任务"""
        # 煎蛋无聊图定时任务
        await asyncio.sleep(5)
        self.printf("初始化定时任务")
        for owner, chat in self.config.items():
            if not re.match(r"[ug]\d+", owner):
                continue
            config = chat.get("jiandan")
            prob = config["probability"]
            crontab = config["cron"]
            if not crontab or prob == 0:
                continue
            cron = MiniCron(crontab, lambda o=owner,c=config: self.jiandan_msg_task(o, c))
            self.printf(f"已为[{owner}]开启煎蛋无聊图定时任务[{crontab}]，概率{prob:.2%}")
            asyncio.run_coroutine_threadsafe(cron.run(), self.robot.loop)

    async def jiandan_msg_task(self, owner: str, config: dict) -> None:
        """自动发送煎蛋无聊图"""
        if random.random() > config["probability"]:
            return
        data_list = self.get_jiandan()
        if not data_list:
            return self.reply("未获取到新的图")
        data = {}
        for item in data_list:
            if item.get("id") not in config["hist"]:
                data = item
                break
            return self.reply("未获取到新的图")
        config["hist"].append(data.get("id"))
        config["hist"] = config["hist"][-10:]
        self.save_config()
        msg = data.get("content")
        msg = re.sub(r"""<img\s+src="([^"]+)"\s*/?>""", r"[CQ:image,file=\1]", msg)
        reply_back(self.robot, owner, msg)

    @via(lambda self: self.au(2) and self.at_or_private()
         and self.match(r"^(来|发)(张|个)(屌|弔|吊)图$"))
    def jiandan_msg(self):
        """获取煎蛋无聊图"""
        config = self.config[self.owner_id]["jiandan"]
        data_list = self.get_jiandan()
        if not data_list:
            return self.reply("未获取到新的图")
        data = {}
        for item in data_list:
            if item.get("id") not in config["hist"]:
                data = item
                break
            return self.reply("未获取到新的图")
        config["hist"].append(data.get("id"))
        config["hist"] = config["hist"][-10:]
        self.save_config()
        msg = data.get("content")
        msg = re.sub(r"""<img\s+src="([^"]+)"\s*/?>""", r"[CQ:image,file=\1]", msg)
        self.reply(msg)

    @via(lambda self: self.au(2) and self.at_or_private()
         and self.match(r"^(\[.*\])?\s*?(打分|评分)(\[.*\])?$"), success=False)
    def nsfw(self):
        """对图片色气度进行打分"""
        api_url = "https://nsfwtag.azurewebsites.net/api/nsfw?url="
        url = ""
        if match := self.match(r"\[CQ:image,.*url=([^,\]]+?),.*\]"):
            url = match.group(1)
        elif msg := self.get_reply():
            if match := re.search(r"\[CQ:image,.*url=([^,\]]+?),.*\]", msg):
                url = match.group(1)
        if url == "":
            return
        self.success = True
        try:
            encoded_url = quote(url, safe="")
            response = httpx.Client().get(api_url + encoded_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                result = data[0]
                neutral = result.get("neutral", 0)
                drawings = result.get("drawings", 0)
                hentai = result.get("hentai", 0)
                porn = result.get("porn", 0)
                sexy = result.get("sexy", 0)
                if neutral > 0.3:
                    return "普通哦"
                category = "二次元" if drawings > 0.3 else "三次元"
                if hentai > 0.3:
                    category += f" hentai{hentai:.1%}"
                if porn > 0.3:
                    category += f" porn{porn:.1%}"
                if sexy > 0.3:
                    category += f" hso{sexy:.1%}"
                if " " not in category:
                    category += "正常图片"
                return self.reply(category, reply=True)
            else:
                return self.reply("API返回格式错误", reply=True)
        except httpx.NetworkError:
            return self.reply("网络请求失败", reply=True)
        except (ValueError, KeyError):
            return self.reply("解析API响应失败", reply=True)

    @via(lambda self: self.au(2) and self.at_or_private()
         and self.match(r"^(来|发|看|给|瑟|涩|se)\S{0,5}(图|瑟|涩|se|好看|好康|可爱)的?"))
    def lolicon(self):
        tags = []
        r18_mode = 0
        if len(self.event.text.split(" ")) > 1:
            tags = self.event.text.split(" ")[1:]
        if self.match(r"(更|超|很|再|无敌)"):
            r18_mode = 1
        try:
            url = ""
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 124)
            self.printf(f"正在使用Lolicon API获取图片...")
            data = self.retry(lambda: self.get_lolicon_image(r18_mode, tags))
            self.printf(f"Lolicon API返回结果:\n{data}", level="DEBUG")
            if data:
                author = f"{data["author"]}(uid: {data["uid"]})"
                title = f"{data["title"]}(pid: {data["pid"]})"
                url = data.get("urls", {}).get("original")
                if data["r18"]:
                    msg = f"来自画师{author}的作品: {title}\n(NSFW图片仅发送URL)\n{url}"
                else:
                    msg = f"来自画师{author}的作品: {title}\n{url}"
            else:
                msg = "未找到该标签的图片"
            self.reply(msg)
            if not data["r18"]:
                self.reply(f"[CQ:image,file={url}]")
        except Exception as e:
            self.errorf(traceback.format_exc())
            self.reply(f"Lolicon API调用失败! {e}", reply=True)

    @via(lambda self: self.au(2) and self.at_or_private()
         and self.config[self.owner_id].get("animate_search")
         and self.match(r"^(\[.*\])?\s*?(搜索|搜|查询|查|找)(番|剧|番剧|动画|动漫)\s*?(\[.*\])?$"))
    def search_animate(self):
        """搜番"""
        url = ""
        if match := self.match(r"\[CQ:image,.*url=([^,\]]+?),.*\]"):
            url = match.group(1)
        elif msg := self.get_reply():
            if match := re.search(r"\[CQ:image,.*url=([^,\]]+?),.*\]", msg):
                url = match.group(1)
        if url == "":
            return self.reply("请附带番剧截图或回复带截图的消息!")
        try:
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 124)
            self.printf(f"正在使用TraceMoe搜索图片[{url}]...")
            msg = self.retry(lambda: self.search_animate_tracemoe(url))
            return self.reply(msg, reply=True)
        except Exception as e:
            self.errorf(traceback.format_exc())
            self.reply(f"TraceMoe调用失败! {e}", reply=True)

    @via(lambda self: self.au(2) and self.at_or_private()
         and self.config[self.owner_id].get("image_search")
         and self.match(r"^(\[.*\])?\s*?(搜索|搜|查询|查|找)(图|图片)\s*?(\[.*\])?$"))
    def search_image(self):
        url = ""
        if match := self.match(r"\[CQ:image,.*url=([^,\]]+?),.*\]"):
            url = match.group(1)
        elif msg := self.get_reply():
            if match := re.search(r"\[CQ:image,.*url=([^,\]]+?),.*\]", msg):
                url = match.group(1)
        if url == "":
            return self.reply("请附带图片或回复带图片的消息!")
        try:
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 124)
            self.printf(f"正在使用谷歌搜图搜索图片[{url}]...")
            success, data = self.retry(lambda: self.search_image_google(url))
            if not success:
                return self.reply(data, reply=True)
            nodes = []
            for img_msg in data:
                nodes.append(build_node(img_msg))
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 66)
            self.reply_forward(nodes, source="谷歌搜图结果")
        except Exception as e:
            self.errorf(traceback.format_exc())
            self.reply(f"谷歌搜图调用失败! {e}", reply=True)

    @via(lambda self: self.au(2)
         and self.config[self.owner_id].get("saucenao")
         and self.match(r"^(\[.*\])?\s*?(s|S)auce(n|N)(a|A)(o|O)"), success=False)
    def saucenao(self):
        url = ""
        if match := self.match(r"\[CQ:image,.*url=([^,\]]+?),.*\]"):
            url = match.group(1)
        elif msg := self.get_reply():
            if match := re.search(r"\[CQ:image,.*url=([^,\]]+?),.*\]", msg):
                url = match.group(1)
        if url == "":
            return
        self.success = True
        try:
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 124)
            self.printf(f"正在使用SauceNAO搜索图片[{url}]...")
            success, data = self.retry(lambda: self.search_image_saucenao(url))
            if not success:
                return self.reply(data, reply=True)
            nodes = []
            for img_msg in data:
                nodes.append(build_node(img_msg))
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 66)
            self.reply_forward(nodes, source="SauceNAO搜索结果")
        except Exception as e:
            self.errorf(traceback.format_exc())
            self.reply(f"SauceNAO调用失败! {e}", reply=True)

    @via(lambda self: self.au(2)
         and self.config[self.owner_id].get("enhance")
         and self.match(r"清晰术"), success=False)
    def enhance_img(self):
        """清晰术"""
        url = ""
        if match := self.match(r"\[CQ:image,.*url=([^,\]]+?),.*\]"):
            url = match.group(1)
        elif msg := self.get_reply():
            if match := re.search(r"\[CQ:image,.*url=([^,\]]+?),.*\]", msg):
                url = match.group(1)
        if url == "":
            return
        self.success = True
        if not self.config.get("real_cugan_url"):
            return self.reply("星辰坐标未对齐，法阵无法唤醒!")
        cmd = self.event.text
        try:
            resp = httpx.Client().get(url)
            img = Image.open(io.BytesIO(resp.content))
            img_width, img_height = img.size
            scale = 2
            con = "conservative"
            # 解析放大倍数
            if "双重" in cmd:
                scale = 2
            elif "三重" in cmd and img_width * img_height < 400000:
                scale = 3
            elif "四重" in cmd and img_width * img_height < 400000:
                scale = 4
            # 解析降噪模式
            if "强力术式" in cmd:
                con = "denoise3x"
            elif "中等术式" in cmd:
                con = "no-denoise" if scale != 2 else "denoise2x"
            elif "弱术式" in cmd:
                con = "no-denoise" if scale != 2 else "denoise1x"
            elif "不变式" in cmd:
                con = "no-denoise"
            elif "原式" in cmd:
                con = "conservative"
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 124)
            self.printf("正在从HuggingFace调用Real-CUGAN模型")
            enhanced_image = self.realCUGAN(resp.content, scale, con)
            enhanced_image_url = re.sub(r"data:image/.*;base64,", "base64://", enhanced_image)
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 66)
            return self.reply(f"[CQ:image,url={enhanced_image_url}]", reply=True)
        except Exception as e:
            self.errorf(traceback.format_exc())
            self.reply(f"{e}", reply=True)

    def realCUGAN(self, img: bytes, scale: int, con: str) -> str:
        """
        Real-CUGAN增强图片清晰度
        :param img: 输入的图片字节流
        :param scale: 放大倍数（如2、3、4）
        :param con: 增强模型的配置（如"conservative", "no-denoise"等）
        :return: 增强后的图片（Base64编码的字符串）
        """
        try:
            predict_url = self.config.get("real_cugan_url")
            model_name = f"up{scale}x-latest-{con}.pth"
            base64_str = base64.b64encode(img).decode("utf-8")
            encoded_image = f"data:image/jpeg;base64,{base64_str}"
            payload = {"data": [encoded_image, model_name, 2]}
            headers = {"Content-Type": "application/json"}
            response = httpx.Client(timeout=300, follow_redirects=True).post(
                predict_url, 
                json=payload, 
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            enhanced_image = result["data"][0]
            return enhanced_image
        except Exception as e:
            raise RuntimeError(f"群星之路被遮蔽，星辉无法汇聚: {str(e)}") from e

    def get_lolicon_image(self, r18: int = 0, tags: list = None) -> dict | None:
        """
        获取LoliconAPI图片
        :param r18: 是否获取R18图片
        :param tags: 需要筛选的标签
        :return: 图片链接
        """
        url = f"https://api.lolicon.app/setu/v2?r18={r18}"
        for tag in tags or []:
            url += f"&tag={quote(tag)}"
        resp = httpx.Client(timeout=5).get(url)
        data = resp.json()
        self.printf(f"调用LoliconAPI({url})返回结果：{data}", level="DEBUG")
        if data.get("data") == []:
            return None
        else:
            img = data["data"][0]
            if url := img.get("urls", {}).get("original"):
                img["urls"]["original"] = url.replace("i.pixiv.re", "i.pximg.org")
            return img

    def search_image_saucenao(self, image_url: str, proxies: str = None) -> Tuple[bool, str | list]:
        """
        SauceNAO搜图
        :param image_url: 图片URL
        :param proxies: 代理配置
        :return: [搜索是否成功, 搜索结果]
        """
        saucenao_key = self.config.get("saucenao_key")
        if not saucenao_key:
            msg = "请先前往[https://saucenao.com/user.php?page=search-api]获取APIKey"
            return False, msg
        saucenao_url = "https://saucenao.com/search.php"
        params = {
            "url": image_url,
            "api_key": saucenao_key,
            "output_type": 2,
            "numres": 3
        }
        resp = httpx.Client(timeout=10, proxy=proxies).get(saucenao_url, params=params)
        if results :=resp.json().get("results"):
            self.printf(f"SauceNAO搜图结果:\n{json.dumps(results, ensure_ascii=False)}", level="DEBUG")
            msg_list = []
            for _, image in enumerate(results):
                header = image.get("header")
                data = image.get("data")
                similarity = header.get("similarity")
                thumbnail = header.get("thumbnail")
                title = data.get("title", "")
                source = data.get("source")
                creator = data.get("creator", "未知")
                author = data.get("author", data.get("artist", creator))
                if isinstance(creator, list):
                    author = ", ".join(creator)
                if data.get("member_name"):
                    author = f"{data.get("member_name")} (uid: {data.get("member_id")})"
                msg = f"{title}"
                msg += f"\n作者: {author}"
                msg += f"\n相似度: {similarity}%"
                if urls := data.get("ext_urls"):
                    msg += f"\n原图地址: {urls[0]}"
                if source:
                    if "i.pximg.net" in source:
                        source = re.sub(r"i\.pximg\.net.*/(\d{5,})", r"www.pixiv.net/artworks/\1", source)
                    msg += f"\n来源: {source}"
                msg += f"\n[CQ:image,file={thumbnail}]"
                msg_list.append(msg)
            return True, msg_list
        elif message := resp.json().get("message"):
            message = message.split("<br />")[0].strip()
            message = re.sub(r"<.*?>", "", message)
            return False, message
        else:
            return False, "SauceNAO返回无结果~"

    def search_image_google(self, image_url: str, proxies: str = None) -> Tuple[bool, str | list]:
        """
        谷歌搜图
        :param image_url: 图片URL
        :param proxies: 代理配置
        :return: [搜索是否成功, 搜索结果]
        """
        serpapi_key = self.config.get("serpapi_key")
        if not serpapi_key:
            msg = "请先前往[https://serpapi.com/manage-api-key]获取APIKey"
            return False, msg
        api_url = "https://serpapi.com/search"
        params = {
            "engine": "google_lens",
            "type": "exact_matches",
            "hl": "zh-cn",
            "api_key": serpapi_key,
            "url": image_url,
        }
        resp = httpx.Client(timeout=10, proxy=proxies).get(api_url, params=params)
        if matches :=resp.json().get("exact_matches"):
            self.printf(f"谷歌搜图结果:\n{json.dumps(matches, ensure_ascii=False)}", level="DEBUG")
            msg_list = []
            for _, data in enumerate(matches[:10]):
                title = data.get("title", "")
                source = data.get("source")
                link = data.get("link")
                thumbnail = data.get("thumbnail")
                date = data.get("date")
                msg = f"{title}"
                msg += f"\n{source}[{link}]"
                if date:
                    msg += f"\n时间: {date}"
                if thumbnail:
                    msg += f"\n[CQ:image,file={thumbnail}]"
                msg_list.append(msg)
            return True, msg_list
        elif message := resp.json().get("error"):
            return False, message
        else:
            return False, "谷歌搜图返回无结果~"

    def search_animate_tracemoe(self, image_url: str, proxies: str = None) -> str:
        """
        TraceMoe 搜图
        :param image_url: 图片URL
        :param proxies: 代理配置
        :return: 搜索结果
        """
        tracemoe_url = "https://api.trace.moe/search?cutBorders&anilistInfo"
        url = f"{tracemoe_url}&url={quote(image_url)}"
        resp = httpx.Client(timeout=10, proxy=proxies).post(url)
        resp.raise_for_status()
        data = resp.json()
        if results := data.get("result"):
            self.printf(f"TraceMoe搜番结果:\n{json.dumps(results, ensure_ascii=False)}", level="DEBUG")
            res = results[0]
            ani = res.get("anilist", {})
            similarity = res.get("similarity", 0) * 100
            title_chs = ani.get("title", {}).get("chinese")
            title_native = ani.get("title", {}).get("native", "")
            title_eng = ani.get("title", {}).get("english", "")
            episode = res.get("episode")
            image = res.get("image")
            at = res.get("at")
            msg = "肯定是"
            if similarity < 0.8:
                msg = "大概是"
            msg += f"《{title_chs or title_native or title_eng}》"
            msg += f"第{episode}集"
            msg += f"的{calc_time(at)}"
            msg += f"\n相似度: {similarity:.2f}%"
            msg += f"\n[CQ:image,file={image}]"
            return msg
        else:
            return "TraceMoe返回无结果~"

    def get_jiandan(self, like: int = 10, raise_error = False) -> str | None:
        """获取一张煎蛋无聊图"""
        try:
            url = "https://jandan.net/api/comment/post/26402?order=desc"
            resp = httpx.Client(timeout=5).get(url)
            resp.raise_for_status()
            if data := resp.json().get("data", {}).get("list"):
                data = [i for i in data if i["vote_positive"] >= like]
                data = sorted(data, key=lambda x: x["vote_positive"])
                if len(data) == 0:
                    return self.printf(f"未获取到最新页满足条件的煎蛋无聊图(like>{like})")
                return data
        except Exception as e:
            if raise_error:
                raise e
            return self.errorf(f"获取煎蛋无聊图失败 {traceback.format_exc()}")

    def retry(self, func: Callable[..., Any], name="", max_retries=3, delay=1, failed_ok=False) -> Any:
        """多次尝试执行"""
        for attempt in range(1, max_retries + 1):
            try:
                result = func()
                return result
            except Exception as e:
                func_name = name if name else func.__name__
                self.printf(f"第 {attempt} 次执行 {func_name} 失败: {e}")
                if attempt == max_retries:
                    if failed_ok:
                        return None
                    raise
                else:
                    self.printf(f"{delay} 秒后重试...")
                    time.sleep(delay)
