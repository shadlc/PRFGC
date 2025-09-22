"""图片处理模块"""

import base64
import io
import re
import traceback
from typing import Tuple
from urllib.parse import quote

import httpx
from PIL import Image

from src.utils import Module, build_node, set_emoji, via

class Picture(Module):
    """图片处理模块"""
    ID = "Picture"
    NAME = "图片处理模块"
    HELP = {
        2: [
            "打分 | 对图片色气度进行打分",
        ],
    }
    GLOBAL_CONFIG = {
        "real_cugan_url": "",
        "saucenao_key": "",
    }

    @via(lambda self: self.au(2) and self.at_or_private()
         and self.match(r"(打分|评分)"), success=False)
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

    @via(lambda self: self.au(2)
         and self.match(r"^(s|S)auce(n|N)(a|A)(o|O)"), success=False)
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
            self.printf("正在使用SauceNAO搜索图片...")
            success, data = self.image_search_saucenao(url)
            if not success:
                return self.reply(data, reply=True)
            self.printf(f"搜索结果:\n{data}", level="DEBUG")
            nodes = []
            for img_msg in data:
                nodes.append(build_node(img_msg))
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 66)
            self.reply_forward(nodes, source="SauceNAO搜索成功")
        except Exception as e:
            self.errorf(traceback.format_exc())
            self.reply(f"SauceNAO调用失败! {e}", reply=True)

    @via(lambda self: self.au(2) and self.at_or_private()
         and self.match(r"^(来|发|看|给|有没有|瑟|涩|se)\S{0,5}(图|瑟|涩|se|好看|好康|可爱)"))
    def lolicon(self):
        tags = ""
        r18_mode = 0
        if len(self.event.text.split(" ")) > 1:
            for tag in self.event.text.split(" ")[1:]:
                tags += "&tag=" + tag
        if self.config[self.owner_id]["R18"] and self.match(r"(更|超|很|再|无敌)"):
            r18_mode = 1
        try:
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 124)
            self.printf("正在使用Lolicon API获取图片...")
            data = self.get_lolicon_image(r18_mode, tags)
            self.printf(f"Lolicon API返回结果:\n{data}", level="DEBUG")
            if data:
                author = f"{data["author"]}(uid:{data["uid"]})"
                title = f"{data["title"]}(pid:{data["pid"]})"
                url = data["urls"]["regular"]
                if r18_mode:
                    msg = f"来自画师{author}的作品{title}\n{url}"
                else:
                    msg = f"来自画师{author}的作品{title}[CQ:image,file={url}]"
            else:
                msg = "未找到该标签的图片"
            return self.reply(msg)
        except Exception as e:
            self.errorf(traceback.format_exc())
            self.reply(f"Lolicon API调用失败! {e}", reply=True)

    @via(lambda self: self.au(2) and self.match(r"清晰术"), success=False)
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

        参数:
            img (bytes): 输入的图片字节流
            scale (int): 放大倍数（如2、3、4）
            con (str): 增强模型的配置（如"conservative", "no-denoise"等）

        返回:
            str: 增强后的图片（Base64编码的字符串）
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

    def get_lolicon_image(self, r18: int = 0, tags: str = "") -> dict | None:
        """
        获取LoliconAPI图片
        :param r18: 是否获取R18图片
        :param tags: 需要筛选的标签
        :return: 图片链接
        """
        url = f"https://api.lolicon.app/setu/v2?r18={r18}{quote(tags)}"
        resp = httpx.Client(timeout=5).get(url)
        data = resp.json()
        self.printf(f"调用LoliconAPI({url})返回结果：{data}", level="DEBUG")
        if data.get("data") == []:
            return None
        else:
            return resp["data"][0]

    def image_search_saucenao(self, image_url: str, proxies: str = None) -> Tuple[bool, str]:
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
        if images :=resp.json().get("results"):
            msg_list = []
            for _, image in enumerate(images):
                header = image.get("header")
                data = image.get("data")
                similarity = header.get("similarity")
                thumbnail = header.get("thumbnail")
                title = data.get("title", "")
                source = data.get("source")
                creator = data.get("creator")
                author = creator
                if isinstance(creator, list):
                    author = ", ".join(creator)
                if not author:
                    author = f"{data.get("member_name")} (uid: {data.get("member_id")})"
                msg = f"标题: {title}"
                msg += f"\n作者: {author}"
                msg += f"\n相似度: {similarity}%"
                if urls := data.get("ext_urls"):
                    msg += f"\n原图地址: {urls[0]}"
                if source:
                    source = source.replace("i.pximg.net", "i.pximg.org")
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
