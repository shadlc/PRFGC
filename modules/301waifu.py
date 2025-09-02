"""抽老婆模块"""
import base64
import html
import imghdr
import os
import random
import datetime
import re
import traceback

import urllib

import httpx
from src.utils import Module, via, get_user_name

class Waifu(Module):
    """抽老婆模块"""
    ID = "Waifu"
    NAME = "抽老婆模块"
    HELP = {
        0: [
            "抽老婆模块，无需使用@，直接发送关键词即可",
        ],
        1: [
            "(开启|关闭)抽老婆 | 开启或关闭本模块功能(需要@)",
        ],
        2: [
            "抽老婆 | 看看今天的二次元老婆是谁",
            "添老婆+人物名称+图片 | 添加老婆",
            "查老婆@某人 | 查询别人老婆",
        ],
    }
    GLOBAL_CONFIG = {
        "pic_path": "waifu",
        "pic_url": "",
    }
    CONV_CONFIG = {
        "enable": True,
        "add_auth": 1,
        "waifu": {}
    }

    def premise(self):
        return self.group_at() or self.config[self.owner_id].get("enable")

    @via(lambda self: self.group_at() and self.au(1) and self.match(r"^(开启|打开|启用|允许|关闭|禁止|不允许|取消)?抽老婆$"))
    def setting(self):
        """设置抽老婆"""
        flag = self.config[self.owner_id]["repeat"]
        text = "开启" if self.config[self.owner_id]["repeat"] else "关闭"
        if self.match(r"(开启|打开|启用|允许)"):
            flag = True
            text = "开启"
        elif self.match(r"(关闭|禁止|不允许|取消)"):
            flag = False
            text = "关闭"
        msg = f"抽老婆功能已{text}"
        self.config[self.owner_id]["enable"] = flag
        self.save_config()
        self.reply(msg, reply=True)

    @via(lambda self: self.au(2) and self.config[self.owner_id].get("enable") and self.match(r"^抽取?老婆$"))
    def draw_waifu(self):
        """抽取二次元老婆"""
        today = datetime.date.today().strftime("%Y%m%d")
        user_id = self.event.user_id
        waives = self.config[self.owner_id]["waifu"]
        waifu = None
        if user_id in waives:
            waifu_name, data_date = waives[user_id]
            if data_date == today:
                waifu = waifu_name
        if waifu is None:
            waifu = self.random_waifu_choice()
        if waifu is None:
            return self.reply("未读取到任何老婆!", reply=True)
        waives[user_id] = [waifu, today]
        self.save_config()
        waifu_name = waifu.split(".")[0]
        waifu_img = self.get_waifu_file(waifu)
        self.reply(f"你今天的二次元老婆是{waifu_name}哒~\n[CQ:image,file=base64://{waifu_img}]", reply=True)

    @via(lambda self: self.au(2) and self.config[self.owner_id].get("enable") and self.match(r"查寻?老婆"))
    def check_waifu(self):
        """查询二次元老婆"""
        today = datetime.date.today().strftime("%Y%m%d")
        user_id = self.event.user_id
        if inputs := self.match(r"\[CQ:at,qq=(.*?)\]"):
            user_id = inputs.groups()[0]
        user_name = get_user_name(self.robot, user_id)
        waives = self.config[self.owner_id]["waifu"]
        waifu = None
        if user_id in waives:
            waifu_name, data_date = waives[user_id]
            if data_date == today:
                waifu = waifu_name
            else:
                return self.reply(f"查询到{user_name}的老婆已过期!", reply=True)
        if waifu is None:
            return self.reply(f"未找到{user_name}的老婆信息!", reply=True)
        waifu_name = waifu.split(".")[0]
        if self.config["pic_url"]:
            self.reply(f"{user_name}的二次元老婆是{waifu_name}哒~\n{self.config["pic_url"]}{urllib.parse.quote(waifu)}", reply=True)
        else:
            waifu_img = self.get_waifu_file(waifu)
            self.reply(f"{user_name}的二次元老婆是{waifu_name}哒~[CQ:image,file=base64://{waifu_img}]", reply=True)

    @via(lambda self: self.au(self.config[self.owner_id].get("add_auth"))
         and self.config[self.owner_id].get("enable") 
         and self.match(r"添加?老婆"))
    def add_waifu(self):
        """添加二次元老婆"""
        try:
            waifu_name = re.sub(r"(添加?老婆)|\[.*\]", "", self.event.msg).strip()
            ret = self.match(r"\[CQ:image,file=(.*)?,url=(.*)\]")
            if not ret:
                return self.reply("请注明二次元老婆名称~")
            elif not ret:
                return self.reply("请附带二次元老婆图片~")
            url = html.unescape(ret.groups()[1])
            self.save_waifu(url, waifu_name)
            self.reply(f"{waifu_name}已增加~", reply=True)
        except Exception:
            self.errorf(traceback.format_exc())
            self.reply(f"{waifu_name}添加失败!", reply=True)

    def get_path(self):
        """获取二次元老婆路径"""
        path = None
        if self.config["pic_path"].startswith("/"):
            path = self.config["pic_path"]
        else:
            path = os.path.join(self.robot.config.data_path, self.config["pic_path"]) 
        os.makedirs(path, exist_ok=True)
        return path       

    def random_waifu_choice(self):
        """随机挑选二次元老婆"""
        pic_path = self.get_path()
        exts = (".jpg", ".jpeg", ".png", ".webp")
        files = [f for f in os.listdir(pic_path) if f.lower().endswith(exts)]
        if len(files) == 0:
            return None
        filename = random.choice(files)
        return filename

    def get_waifu_file(self, filename: str):
        """下载二次元老婆"""
        pic_path = self.get_path()
        filepath = os.path.join(pic_path, filename)
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def save_waifu(self, url: str, name: str):
        """保存二次元老婆"""
        pic_path = self.get_path()
        data = httpx.Client().get(url, timeout=10)
        data.raise_for_status()
        fmt = imghdr.what(None, h=data.content)
        file_path = os.path.join(pic_path, f"{name}.{fmt}")
        with open(file_path, "wb") as f:
            f.write(data)
                    
