"""视频下载模块"""

import base64
import os
import re
from http.cookiejar import LoadError
import time

import urllib
from yt_dlp import YoutubeDL, DownloadError

from src.utils import Module, build_node, calc_size, calc_time, format_to_log, get_forward_msg, get_image_base64, get_msg, status_ok, via

class Ytdlp(Module):
    """视频下载模块"""

    ID = "Ytdlp"
    NAME = "视频下载模块"
    HELP = {
        2: [
            "本模块主要是为了方便在不打开视频链接的情况下观看视频使用，回复视频链接、小程序并@即可获取视频文件",
        ],
    }
    CONFIG = "ytdlp.json"
    GLOBAL_CONFIG = {
        "base_path": "ytdlp",
        "headers": {},
        "ydl": {
            "paths": {
                "home": "data/ytdlp",
            },
            "outtmpl": {
                "default": "%(title)s [%(extractor)s %(id)s]",
                "chapter": "%(title)s - %(section_number)03d %(section_title)s [%(extractor)s %(id)s]"
            },
            "proxy": "",
            "extractor_args": "youtubetab:skip=authcheck youtube:player-client=web",
            "merge_output_format": "mp4",
            "format": "wv+wa",
        },
    }
    CONV_CONFIG = {
        "enable": True,
        "cool_down": 600,
        "tasks": {},
    }

    def __init__(self, event, auth = 0):
        self.video_pattern = r"(https?://[^\"]*(b23.tv|bilibili.com|youtu.be|youtube.com|v.qq.com|douyin.com|tiktok.com)[^\s?@]*)"
        super().__init__(event, auth)

    @via(lambda self: self.at_or_private() and self.au(2)
            and self.config[self.owner_id]["enable"]
            and (self.match(r"\[CQ:reply,id=([^\]]+?)\]")
            or self.match(self.video_pattern)), success=False)
    def info(self):
        """获取视频信息"""
        url_match = self.match(self.video_pattern)
        reply_match = self.match(r"\[CQ:reply,id=([^\]]+?)\]")
        url = ""
        if reply_match:
            msg_id = reply_match.groups()[0]
            reply_msg = get_msg(self.robot, msg_id)
            msg = reply_msg["data"]["message"].replace("\\", "")
            if not status_ok(reply_msg):
                return
            if re.search("下载视频", msg) or re.search("下载视频", self.event.msg):
                return
            if re.search(self.video_pattern, msg):
                url_match = re.search(self.video_pattern, msg)
            forward_match = self.match(r"\[CQ:forward,id=([^\]]+?)\]")
            if forward_match:
                msg_id = reply_match.groups()[0]
                forward_msg = get_forward_msg(self.robot, msg_id)
                msg = str(forward_msg["data"]["messages"])
                if re.search(self.video_pattern, msg):
                    url_match = re.search(self.video_pattern, msg)
            if not url_match:
                return
        elif self.match("下载视频"):
            return
        url = url_match.groups()[0]
        opts = self.get_option(url)
        try:
            info = self.get_info(url, opts)
            msg = self.parse_info(info)
            if "entries" in info:
                msg = f"解析成功，但不支持下载视频合辑，请使用单集链接!\n{msg}"
            else:
                msg = f"视频解析成功!\n{msg}"
            self.reply(msg, reply=True)
            self.success = True
        except LoadError:
            # http://fileformats.archiveteam.org/wiki/Netscape_cookies.txt
            return self.reply("Cookie载入失败! 请联系管理员", reply=True)
        except DownloadError as e:
            nodes = build_node(f"{format_to_log(e.msg)}")
            return self.reply_forward(nodes, source="视频解析失败")

    @via(lambda self: self.at_or_private() and self.au(2)
            and self.config[self.owner_id]["enable"]
            and (self.match(r"\[CQ:reply,id=([^\]]+?)\]")
            or self.match("下载视频")), success=False)
    def download(self):
        """下载视频"""
        url_match = self.match(self.video_pattern)
        reply_match = self.match(r"\[CQ:reply,id=([^\]]+?)\]")
        url = ""
        if reply_match:
            msg_id = reply_match.groups()[0]
            reply_msg = get_msg(self.robot, msg_id)
            if not status_ok(reply_msg):
                return
            msg = reply_msg["data"]["message"]
            if "下载视频" not in msg and "下载视频" not in self.event.msg:
                return
            if re.search(self.video_pattern, msg):
                url_match = re.search(self.video_pattern, msg)
            forward_match = self.match(r"\[CQ:forward,id=([^\]]+?)\]")
            if forward_match:
                msg_id = reply_match.groups()[0]
                forward_msg = get_forward_msg(self.robot, msg_id)
                msg = str(forward_msg["data"]["messages"])
                if re.search(self.video_pattern, msg):
                    url_match = re.search(self.video_pattern, msg)
        elif not self.match("下载视频"):
            return
        if not url_match:
            return
        try:
            tasks = self.config[self.owner_id]["tasks"]
            url = url_match.groups()[0]
            opts = self.get_option(url)
            info = self.get_info(url, opts)
            user_id = self.event.user_id
            user_task = tasks.get(user_id)
            cool_down = self.config[self.owner_id]["cool_down"]
            if self.event.user_id in self.robot.config.admin_list:
                pass
            elif user_task and time.time() - int(user_task[-1][2]) < cool_down:
                remain = int(cool_down - time.time() + int(user_task[-1][2]))
                self.reply(f"视频下载功能每{cool_down}秒才能使用一次，你还剩{remain}秒", reply=True)
                return
            if user_id not in self.config[self.owner_id]["tasks"]:
                self.config[self.owner_id]["tasks"][user_id] = []
            self.config[self.owner_id]["tasks"][user_id].append([
                info["url"], user_id, str(int(time.time()))
            ])
            self.save_config()
            name = info["title"]
            if info["series"]:
                name = f"{info["series"]} {info["title"]}"
            msg = f"正在解析视频[{name}]，请耐心等待"
            self.reply(msg, reply=True)
            ext = self.config["ydl"]["merge_output_format"]
            video_path = self.download_video(info["url"], opts)
            video_path = f"{video_path}.{ext}"
            with open(video_path, "rb") as video_file:
                video_bytes = video_file.read()
                base64_bytes = base64.b64encode(video_bytes)
                base64_string = base64_bytes.decode("utf-8")
                msg = f"[CQ:video,file=base64://{base64_string}]"
                self.reply(msg)
            os.remove(video_path)
        except LoadError:
            # http://fileformats.archiveteam.org/wiki/Netscape_cookies.txt
            return self.reply("Cookie载入失败! 请联系管理员", reply=True)
        except DownloadError as e:
            self.config[self.owner_id]["tasks"][user_id].pop()
            nodes = build_node(f"{format_to_log(e.msg)}")
            return self.reply_forward(nodes, source="视频解析失败")
        self.success = True

    def get_option(self, url: str) -> dict:
        """获取配置参数"""
        opts = self.config["ydl"].copy()
        cookie_path = self.get_cookie(url)
        if cookie_path:
            opts["cookiefile"] = cookie_path
        return opts

    def get_cookie(self, url: str) -> str:
        """获取Cookie"""
        cookies_path = os.path.join(self.robot.config.data_path, self.config["base_path"], "cookies")
        os.makedirs(cookies_path, exist_ok=True)
        path = None
        if re.search(r"(b23.tv|bilibili.com)", url):
            path = os.path.join(cookies_path, "bilibili.txt")
        elif re.search(r"(youtu.be|youtube.com)", url):
            path = os.path.join(cookies_path, "youtube.txt")
        elif re.search(r"(v.qq.com)", url):
            path = os.path.join(cookies_path, "qqvideo.txt")
        elif re.search(r"(douyin.com)", url):
            path = os.path.join(cookies_path, "douyin.txt")
        elif re.search(r"(tiktok.com)", url):
            path = os.path.join(cookies_path, "tiktok.txt")
        if path and os.path.exists(path):
            return path

    def get_info(self, url: str, opts: dict) -> dict:
        """获取信息"""
        try:
            req = urllib.request.Request(url, headers=self.config.get("headers"))
            with urllib.request.urlopen(req) as response:
                url = response.url
        except Exception as e:
            if self.robot.config.is_debug:
                self.warnf(f"获取重定向url失败! {e}")
        info = YoutubeDL(opts).extract_info(url, download=False, process=False)
        url = info.get("webpage_url", "")
        url = url.split("?")[0]
        site = info.get("extractor", "")
        series = info.get("series", "")
        title = info.get("title", "[未知]")
        if info.get("_type") == "playlist":
            description = info.get("description", "")
            return {
                "type": "playlist",
                "url": url,
                "site": site,
                "series": series,
                "title": title,
                "description": description,
            }
        else:
            description = info.get("description", "")
            uploader = info.get("uploader", "")
            duration = info.get("duration", 0)
            thumbnail = info.get("thumbnail", "")
            ext = info.get("ext", "[未知格式]")
            resolution = info.get("resolution", "[未知分辨率]")
            size = info.get("size", 0)
            view_count = info.get("view_count", 0)
            img = get_image_base64(self.robot, thumbnail)
            return {
                "type": "video",
                "url": url,
                "site": site,
                "series": series,
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "img": img,
                "ext": ext,
                "resolution": resolution,
                "size": size,
                "view_count": view_count,
            }

    def parse_info(self, info: dict) -> str:
        """格式化视频信息为文本"""
        video_type = info.get("type")
        url = info.get("url")
        site = info.get("site")
        series = info.get("series")
        title = info.get("title")
        description = info.get("description")
        uploader = info.get("uploader")
        duration = info.get("duration")
        img = info.get("img")
        ext = info.get("ext")
        resolution = info.get("resolution")
        size = info.get("size")
        view_count = info.get("view_count")
        view_count = f"{round(view_count/10000,2)}万" if view_count >= 10000 else view_count
        if video_type == "playlist":
            msg = f"链接: {url}\n"
            msg += f"平台: {site}\n"
            msg += f"标题: {title}\n"
            msg += f"简介: {description}"
            return msg
        else:
            msg = f"链接: {url}\n"
            msg += f"平台: {site}\n"
            if series:
                msg += f"标题: {series} {title}\n"
            else:
                msg += f"标题: {title}\n"
            msg += f"作者: {uploader or "[未知]"}\n"
            msg += f"时长: {calc_time(int(duration)) or "[未知]"}\n"
            msg += f"播放量: {view_count}\n"
            if img:
                msg += f"[CQ:image,file=base64://{img},subtype=0]"
            if size:
                msg += "\n获取到的最佳格式为: "
                msg += f"{resolution} {ext} {calc_size(int(size))}"
            msg += "\n@我并回复本条消息开始下载视频"
            return msg

    def download_video(self, url: str, opts: dict) -> str:
        """下载视频"""
        with YoutubeDL(opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename
