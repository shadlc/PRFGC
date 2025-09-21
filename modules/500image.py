"""图片处理模块"""

import re
from urllib.parse import quote

import httpx

from src.utils import Module, get_msg, status_ok, via

class Image(Module):
    """图片处理模块"""
    ID = "Image"
    NAME = "图片处理模块"
    HELP = {
        2: [
            "打分 | 对图片色气度进行打分",
        ],
    }

    @via(lambda self: self.au(2)
         and self.match(r"打分"), success=False)
    def nsfw(self):
        """对图片色气度进行打分"""
        api_url = "https://nsfwtag.azurewebsites.net/api/nsfw?url="
        reply_match = self.match(r"\[CQ:reply,id=([^\]]+?)\]")
        url = ""
        if match := self.match(r"\[CQ:image,.*url=([^,\]]+?),.*\]"):
            url = match.group(1)
        elif reply_match:
            msg_id = reply_match.group(1)
            reply_msg = get_msg(self.robot, msg_id)
            if not status_ok(reply_msg):
                return
            msg = reply_msg["data"]["message"].replace("\\", "")
            if match := re.match(r"\[CQ:image,.*url=([^,\]]+?),.*\]", msg):
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
