"""外部请求模块处理"""

import copy
import json
import re
import socket
import time
import threading
import traceback
from collections import deque

from colorama import Fore

from src.api import send_msg
from src.utils import Module, listening


class Webhook(Module):
    """外部请求模块处理"""
    ID = "Webhook"
    NAME = "外部请求模块处理"
    HELP = {
        1: [
            "开启/关闭 | 开启或关闭外部请求通知",
        ],
    }
    CONFIG = "webhook.json"
    GLOBAL_CONFIG = {
      "host": "127.0.0.1",
      "port": 3009,
      "admin_id": "",
      "admin_warning_delay": 3600,
      "notify": {},
    }
    AUTO_INIT = True
    def __init__(self, event, auth=0):
        super().__init__(event, auth)
        if hasattr(self.robot, "webhook"):
            return
        self.latest_warning_time = 0
        self.msg_deque = deque(maxlen=20)
        self.msg_imm_deque = deque(maxlen=10)
        threading.Thread(target=self.hooking, daemon=True).start()
        self.robot.webhook = self

    def hooking(self):
        self.printf(f"正在监听: {Fore.GREEN}{self.config["host"]}:{self.config["port"]}{Fore.RESET}")
        while True:
            try:
                data = self.receive_msg()
                threading.Thread(target=self.handle_msg, args=(data,), daemon=True).start()
                time.sleep(0.01)
            except Exception:
                msg = f"[{self.NAME}]出现致命错误\n{traceback.format_exc()}"
                self.errorf(msg)
                if self.config["admin_id"] and (
                    time.time() - self.latest_warning_time > self.config["admin_warning_delay"]
                ):
                    send_msg(self, {
                        "msg_type":"private",
                        "number": self.config["admin_id"],
                        "msg": msg
                    })
                    self.latest_warning_time = time.time()
                time.sleep(5)

    def receive_msg(self):
        try:
            header, body = listening(self.config["host"], self.config["port"])
            if self.robot.config.is_debug and header.get("Content-Type") != "application/json":
                self.warnf(f"收到一非JSON数据\n{body}")
                return {}
            elif header.get("Transfer-Encoding") == "chunked":
                body = body.split("\r\n", maxsplit=1)[1].strip()
                rev_json = json.loads(body)
                return rev_json
            else:
                rev_json = json.loads(body)
                return rev_json
        except socket.gaierror:
            self.errorf(f"绑定地址有误！ {self.config["host"]}:{self.config["port"]} 不是一个正确的可绑定地址")
        except json.JSONDecodeError:
            self.warnf("JSON数据解析失败！")
            return {}

    def handle_msg(self, data: dict):
        msg_type = ""
        for type_name in data:
            if type_name in ["type", "Event"]:
                msg_type = data.get(type_name)
        if data.get("status") == "firing":
            msg_type = "GRAFANA_ALERT"

        msg = json.dumps(data)

        if msg_type == "":
            self.warnf(f"接收到一条类型未知类型的外部请求 {msg}")
            return

        self.printf(f"接收到一条类型为{msg_type}的外部请求")
        if self.robot.config.is_debug:
            self.warnf(f"{data}")

        if self.msg_has_reported(data):
            self.warnf("此外部请求近期已经通报过，已忽略")
            return

        self.msg_imm_deque.append({"type": msg_type, "timestamp": time.time(), "msg": msg,})

        if msg_type == "STREAM_STARTED":
            if (not self.repeat(msg_type=msg_type)
                and not self.happen("STREAM_STOPPED", 5, imm=True)
                and not self.occur("STREAM_STOPPED", 5)
            ):
                self.stream_start(data)
            else:
                self.warnf(f"{msg_type}已取消通告")
        elif msg_type == "STREAM_STOPPED":
            if (not self.repeat(msg_type=msg_type)
                and not self.happen("STREAM_STARTED", 5, imm=True)
                and not self.occur("STREAM_STARTED", 5)
            ):
                self.stream_end(data)
            else:
                self.warnf(f"{msg_type}已取消通告")
        elif msg_type == "library.new":
            if not self.repeat(msg_type=msg_type):
                self.emby_new(data)
            else:
                self.warnf(f"{msg_type}已取消通告")
        elif msg_type == "GRAFANA_ALERT":
            self.grafana_alert(data)

        self.msg_deque.append({"type": msg_type, "timestamp": int(time.time()), "msg": msg,})

    def msg_has_reported(self, data: str, period=86400):
        """判断消息是否已经通告过"""
        if len(self.msg_deque) == 0:
            return False
        reported = False
            
        if json.dumps(data) in self.msg_deque:
            reported = True
        elif (
            data.get("Item", {}).get("SeriesName")
            and any(data.get("Item", {}).get("SeriesName") in i["msg"] for i in self.msg_deque)
        ):
            reported = True

        if period != 0 and time.time() - self.msg_deque[-1]["timestamp"] < period:
            reported = False
        return reported

    def repeat(self, times=2, msg_type: str|None=None, msg: str|None=None):
        """重复汇报大于等于给定次数"""
        if len(self.msg_deque) == 0:
            return False
        if ((msg_type and msg_type == self.msg_deque[-1]["type"])
            or (msg and msg == self.msg_deque[-1]["msg"])
        ):
            latest_times = 0
            for i in reversed(self.msg_deque):
                if ((msg_type and msg_type in i["type"])
                    or (msg and msg in i["msg"])
                ):
                    latest_times += 1
                else:
                    break
            if latest_times >= times:
                self.warnf(f"重复执行次数达到{times}次而取消通知")
                return True
        return False

    def happen(self, msg_type: str, second: int, imm=False):
        """指定类型的通知是否在给定秒数内执行过"""
        msg_deque = list(self.msg_imm_deque)[:-1] if imm else self.msg_deque
        for i in reversed(msg_deque):
            require_second = round(second - time.time() + i["timestamp"], 2)
            if require_second <= 0:
                break
            if msg_type == i["type"]:
                self.warnf(f"因{second}秒内发生过{msg_type}类型通知而取消通知(仍需{require_second}秒)")
                return True
        return False

    def occur(self, msg_type: str, second: int):
        """指定类型的通知是否在给定秒数中被执行"""
        ori_deque = copy.deepcopy(self.msg_imm_deque)
        time.sleep(second)
        new_msg_list = [i for i in self.msg_imm_deque if i not in ori_deque]
        for i in new_msg_list:
            if msg_type == i["type"]:
                self.warnf(f"因在{second}内收到了通知{msg_type}而取消通知")
                return True
        return False

    def stream_start(self, data):
        """OwnCast开始直播通知"""
        name = data.get("eventData").get("name")
        title = data.get("eventData").get("streamTitle")
        summary = data.get("eventData").get("summary")
        if notify := self.config["notify"].get("STREAM_STARTED"):
            for i in notify:
                send_msg(self.robot, {
                    "msg_type": i.get("msg_type"),
                    "number": i.get("number"),
                    "msg": i.get("msg", "").format(name=name, title=title, summary=summary)
                })

    def stream_end(self, data):
        """OwnCast结束直播通知"""
        name = data.get("eventData").get("name")
        if notify := self.config["notify"].get("STREAM_STOPPED"):
            for i in notify:
                send_msg(self.robot, {
                    "msg_type": i.get("msg_type"),
                    "number": i.get("number"),
                    "msg": i.get("msg", "").format(name=name)
                })

    def emby_new(self, data):
        """Emby更新资源"""
        item = data.get("Item")
        if not item or item.get("Type")  == "Recording":
            return
        if "新建 " in data.get("Title"):
            name = data.get("Title").split("新建 ")[-1]
        elif "项到" in data.get("Title"):
            name = data.get("Title").split("项到")[-1]
        else:
            name = data.get("Title")
        img_id = item.get("Id","")
        if notify := self.config["notify"].get("library.new"):
            for i in notify:
                if re.search(i.get("keywords", ""), name):
                    send_msg(self.robot, {
                        "msg_type": i.get("msg_type"),
                        "number": i.get("number"),
                        "msg": i.get("msg", "").format(name=name, img_id=img_id)
                    })

    def grafana_alert(self, data):
        """Grafana警告"""
        if not data.get("alerts"):
            return
        title = data.get("title")
        if notify := self.config["notify"].get("STREAM_STARTED"):
            for i in notify:
                send_msg(self.robot, {
                    "msg_type": i.get("msg_type"),
                    "number": i.get("number"),
                    "msg": i.get("msg", "").format(title=title)
                })
