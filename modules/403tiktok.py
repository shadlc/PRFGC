"""抖音视频模块"""

import re
import traceback

import httpx

from src.utils import Module, set_emoji, via

class Tiktok(Module):
    """抖音视频模块"""

    ID = "Tiktok"
    NAME = "抖音视频模块"
    HELP = {
        0: [
            "本模块用于解析抖音视频，回复视频链接、小程序并@即可获取视频文件",
        ],
    }

    def __init__(self, event, auth = 0):
        self.video_pattern = r"(https?://[^\s@&;,\"]*(douyin.com|tiktok.com)[^\s@&;,\"]*)"
        super().__init__(event, auth)

    @via(lambda self: self.at_or_private() and self.au(2)
            and (self.is_reply() or self.match(self.video_pattern)), success=False)
    def tiktok_download(self):
        """下载视频"""
        url = ""
        if match := self.match(rf"({self.video_pattern})"):
            url = match.group(1)
        elif msg := self.get_reply():
            if match := re.search(rf"({self.video_pattern})", msg):
                url = match.group(1)
        if url == "":
            return
        self.success = True
        try:
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 124)
            api_url = f"https://api.pearktrue.cn/api/video/douyin/?url={url}"
            resp = httpx.Client(follow_redirects=True).get(api_url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 200:
                self.reply(f"抖音视频解析失败，错误信息：{data.get("msg", "未知错误")}", reply=True)
                return
            if not self.is_private():
                set_emoji(self.robot, self.event.msg_id, 66)
            msg = f"[CQ:video,file={data["data"]["url"]}]"
            self.reply(msg)
        except Exception:
            nodes = self.node(f"{traceback.format_exc()}")
            return self.reply_forward(nodes, source="抖音视频处理失败")
