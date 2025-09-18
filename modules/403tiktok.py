"""抖音视频模块"""

import re
import traceback

import httpx

from src.utils import Module, get_msg, set_emoji, status_ok, via

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
            and (self.match(r"\[CQ:reply,id=([^\]]+?)\]")
            or self.match(self.video_pattern)), success=False)
    def download(self):
        """下载视频"""
        url_match = self.match(rf"({self.video_pattern})")
        reply_match = self.match(r"\[CQ:reply,id=([^\]]+?)\]")
        url = ""
        if reply_match:
            msg_id = reply_match.group(1)
            reply_msg = get_msg(self.robot, msg_id)
            if not status_ok(reply_msg):
                return
            msg = reply_msg["data"]["message"].replace("\\", "")
            if re.search(self.video_pattern, msg):
                url_match = re.search(self.video_pattern, msg)
        if not url_match:
            return
        url = url_match.group(1)
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
