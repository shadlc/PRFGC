"""视频下载模块"""

import base64
import logging
import os
from pathlib import Path
import re
from http.cookiejar import LoadError
import time

import traceback
import urllib
from yt_dlp import YoutubeDL, DownloadError

from src.utils import Module, apply_formatter, build_node, calc_size, calc_time, format_to_log, get_forward_msg, get_image_base64, get_msg, set_emoji, status_ok, via

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
        "video_path": "", # 如果不使用base64传输，则填入此路径，应该保证QQ API部分程序能获取到相同的对应路径下的文件
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
            "format": "bv*+ba/b",
        },
    }
    CONV_CONFIG = {
        "enable": True,
        "cool_down": 600,
        "tasks": {},
    }

    def __init__(self, event, auth = 0):
        self.video_pattern = r"(https?://[^\s?@;,\"]*(b23.tv|bilibili.com|youtu.be|youtube.com|v.qq.com|douyin.com|tiktok.com)[^\s?@;,\"]*)"
        super().__init__(event, auth)

    @via(lambda self: self.at_or_private() and self.au(2)
            and self.config[self.owner_id]["enable"]
            and (self.match(r"\[CQ:reply,id=([^\]]+?)\]")
            or self.match("视频详情")), success=False)
    def info(self):
        """获取视频详情"""
        url_match = self.match(rf"^视?频?详?情?\s?({self.video_pattern})\s?视?频?详?情?$")
        reply_match = self.match(r"\[CQ:reply,id=([^\]]+?)\]")
        url = ""
        if reply_match:
            msg_id = reply_match.groups()[0]
            reply_msg = get_msg(self.robot, msg_id)
            msg = reply_msg["data"]["message"].replace("\\", "")
            if not status_ok(reply_msg):
                return
            if "视频详情" not in msg and "视频详情" not in self.event.msg:
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
        elif not self.match("视频详情"):
            return
        if not url_match:
            return
        url = url_match.groups()[0]
        opts = self.get_option(url)
        try:
            set_emoji(self.robot, self.event.msg_id, 124)
            info = self.get_info(url, opts)
            msg = self.parse_info(info)
            if info.get("type") == "playlist":
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
        except Exception as e:
            nodes = build_node(f"{e}")
            return self.reply_forward(nodes, source="视频解析失败")

    @via(lambda self: self.at_or_private() and self.au(2)
            and self.config[self.owner_id]["enable"]
            and (self.match(r"\[CQ:reply,id=([^\]]+?)\]")
            or self.match(self.video_pattern)), success=False)
    def download(self):
        """下载视频"""
        url_match = self.match(rf"^({self.video_pattern})$")
        reply_match = self.match(r"\[CQ:reply,id=([^\]]+?)\]")
        url = ""
        if reply_match:
            msg_id = reply_match.groups()[0]
            reply_msg = get_msg(self.robot, msg_id)
            if not status_ok(reply_msg):
                return
            msg = reply_msg["data"]["message"].replace("\\", "")
            if "视频详情" in msg or "视频详情" in self.event.msg:
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
        elif self.match("视频详情"):
            return
        if not url_match:
            return
        video_path = ""
        tasks = self.config[self.owner_id]["tasks"]
        url = url_match.groups()[0]
        opts = self.get_option(url)
        try:
            set_emoji(self.robot, self.event.msg_id, 124)
            info = self.get_info(url, opts)
            if info.get("type") == "playlist":
                msg = self.parse_info(info)
                msg = f"解析成功，但不支持下载视频合辑，请使用单集链接!\n{msg}"
                self.reply(msg)
                return
            user_id = self.event.user_id
            user_task = tasks.get(user_id)
            cool_down = self.config[self.owner_id]["cool_down"]
            if self.event.user_id in self.robot.config.admin_list:
                pass
            elif user_task and time.time() - int(user_task[-1][2]) < cool_down:
                remain = int(cool_down - time.time() + int(user_task[-1][2]))
                self.reply(f"视频解析功能每{cool_down}秒才能使用一次，你还剩{remain}秒", reply=True)
                return
            if user_id not in self.config[self.owner_id]["tasks"]:
                self.config[self.owner_id]["tasks"][user_id] = []
            self.config[self.owner_id]["tasks"][user_id].append([
                info["url"], user_id, str(int(time.time()))
            ])
            self.save_config()
            if info["duration"] > 600:
                name = info["title"]
                if series := info["series"]:
                    name = f"{series} {name}"
                if uploader := info["uploader"]:
                    name = f"{uploader}上传的视频[{name}]"
                else:
                    name = f"视频[{name}]"
                msg = f"视频大于十分钟,仅能使用最低分辨率下载，正在解析{name}，请耐心等待"
                self.reply(msg, reply=True)
                opts["format"] = "wv+ba/w"
            elif info["duration"] > 300:
                opts["format"] = "bv[height<=1000]+ba/b"
            set_emoji(self.robot, self.event.msg_id, 60)
            ext = self.config["ydl"]["merge_output_format"]
            dir_path = Path(self.download_video(info["url"], opts)).as_posix()
            file_path = f"{dir_path}.{ext}"
            video_name = file_path.split("/").pop()
            set_emoji(self.robot, self.event.msg_id, 66)
            if video_path := self.config["video_path"]:
                video_path = Path(os.path.join(video_path, video_name)).as_posix()
                msg = f"[CQ:video,file=file://{urllib.parse.quote(video_path)}]"
                self.reply(msg)
            else:
                with open(file_path, "rb") as video_file:
                    video_bytes = video_file.read()
                    base64_bytes = base64.b64encode(video_bytes)
                    base64_string = base64_bytes.decode("utf-8")
                    msg = f"[CQ:video,file=base64://{base64_string}]"
                    self.reply(msg)
        except LoadError:
            # http://fileformats.archiveteam.org/wiki/Netscape_cookies.txt
            return self.reply("Cookie载入失败! 请联系管理员", reply=True)
        except DownloadError as e:
            nodes = build_node(f"{format_to_log(e.msg)}")
            return self.reply_forward(nodes, source="视频解析失败")
        except Exception:
            nodes = build_node(f"{traceback.format_exc()}")
            return self.reply_forward(nodes, source="视频处理失败")
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)
        self.success = True

    @via(
        lambda self: self.at_or_private() and self.au(1)
        and self.match(r"^(开启|启用|打开|记录|启动|关闭|禁用|取消)视频(解析|下载)?(功能)?$")
    )
    def enable(self):
        """启用视频模块功能"""
        msg = ""
        if self.match(r"(开启|启用|打开|记录|启动)"):
            self.config[self.owner_id]["enable"] = True
            msg = "视频解析功能已开启"
            self.save_config()
        elif self.match(r"(关闭|禁用|取消)"):
            self.config[self.owner_id]["enable"] = False
            msg = "视频解析功能已关闭"
            self.save_config()
        self.reply(msg)

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
        if view_count:
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
