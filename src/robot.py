"""机器人类定义"""

import asyncio
import importlib
import json
import logging
import os
import random
import re
import time
import threading
import traceback

from collections import deque
from colorama import Fore
import httpx

from src import api
from src.config import Config
from src.utils import (
    Event, Module, format_to_log, handle_placeholder, import_json, msg_img2char, reply_event, scan_missing_modules, simplify_traceback, receive_msg, send_msg, status_ok
)
from src.command import ExecuteCmd

logger = logging.getLogger()

class Memory(object):
    """独立聊天记录存储"""  
    def __init__(self):
        self.past_message = deque(maxlen=20)
        self.past_notice = deque(maxlen=20)


class Concerto:
    """机器人类定义"""

    def __init__(self):
        self.is_running = True
        self.is_restart = False

        self.config_file = "data/config.json"
        self.config = Config(self.config_file)
        self.cmd = {}

        self.func = {} # 需要开放为全局函数的字典
        self.modules = {} # 所有载入模块字典
        self.persist_mods = {} # 需要持续性运行的模块
        self.placeholder_dict = import_json(
            os.path.join(self.config.data_path, self.config.lang_file)
        ).get("placeholder", {})

        self.api_name = ""
        self.self_id = ""
        self.self_name = ""
        self.at_info = ""
        self.request_list = deque(maxlen=20)
        self.self_message = deque(maxlen=20)
        self.user_dict = {}
        self.group_dict = {}
        self.data: dict[str, Memory] = {}
        self.past_message = deque(maxlen=20)
        self.past_notice = deque(maxlen=20)
        self.past_request = deque(maxlen=20)
        self.latest_data = {}

        self.start_info = """
    __                           __        
   /  )                  _/_    /  )    _/_
  /   __ ____  _. _  __  /  __ /--<  __ /  
 (__/(_)/ / <_(__</_/ (_<__(_)/___/_(_)<__ 
        """
        self.printf(
            random.choice([Fore.RED,Fore.GREEN,Fore.YELLOW,Fore.BLUE,Fore.MAGENTA,Fore.CYAN,Fore.WHITE])
            + self.start_info + Fore.RESET, flush=True)

    def run(self) -> bool:
        """尝试连接到API"""
        self.printf(f"正在连接API[{Fore.GREEN}{self.config.api_base}{Fore.RESET}]...", end="", console=False)
        connected = False
        while not connected:
            self.printf(".", end="", flush=True)
            try:
                result = api.get(self, "/get_version_info")
                connected = status_ok(result)
                app_name = result.get("data",{}).get("app_name")
                app_version = result.get("data",{}).get("app_version")
                self.printf(f"已连接至 {Fore.YELLOW}{app_name}v{app_version}{Fore.RESET}", flush=True)
                self.api_name = f"{app_name}v{app_version}"
                result = api.get(self, "/get_login_info")
                self.self_name = result["data"]["nickname"]
                self.self_id = str(result["data"]["user_id"])
                self.at_info = "[CQ:at,qq=" + str(self.self_id) + "]"
                self.printf(f"已接入账号: {Fore.MAGENTA}{self.self_name}({self.self_id}){Fore.RESET}")
            except httpx.RequestError:
                time.sleep(1)
                continue
            time.sleep(1)
        self.import_modules()
        return connected

    def listening_console(self):
        """监听来自终端的输入并处理"""
        while self.is_running:
            self.handle_console(input(f"\r{Fore.GREEN}<console> {Fore.RESET}"))

    def listening_msg(self):
        """监听来自qq的请求"""
        self.printf(f"正在监听: {Fore.GREEN}{self.config.host}:{self.config.port}{Fore.RESET}")
        while self.is_running:
            rev = receive_msg(self)
            threading.Thread(target=self.handle_msg, args=(rev,), daemon=True).start()

    def handle_msg(self, rev):
        """消息处理接口主函数"""

        if not rev or rev == {}:
            return

        event = Event(self, rev)
        user_id = event.user_id
        group_id = event.group_id

        # 如果是调试模式，输出所有接收到的原始信息
        if self.config.is_debug and not event.post_type == "meta_event":
            self.printf(
                f"{Fore.YELLOW}[DATA]{Fore.RESET} 接收数据包 "
                f"{Fore.YELLOW}{json.dumps(rev, ensure_ascii=False)}{Fore.RESET}"
            )

        # 数据存储到对应的data中, 并获取data
        if user_id == self.self_id or user_id in self.config.blacklist:
            pass
        elif group_id:
            if ("g" + str(group_id)) not in self.data:
                self.data["g" + str(group_id)] = Memory()
            data = self.data["g" + str(group_id)]
            self.latest_data = "g" + str(group_id)
        elif user_id:
            if ("u" + str(user_id)) not in self.data:
                self.data["u" + str(user_id)] = Memory()
            data = self.data["u" + str(user_id)]
            self.latest_data = "u" + str(user_id)
        else:
            if ("u" + str(self.self_id)) not in self.data:
                self.data["u" + str(self.self_id)] = Memory()
            data = self.data["u" + str(self.self_id)]

        # 分类处理消息，不处理自身与黑名单用户
        if user_id == self.self_id or user_id in self.config.blacklist:
            pass
        elif event.post_type == "message":
            data.past_message.append(rev)
            if str(user_id) in self.config.admin_list:
                return self.message(event, 1)
            elif group_id:
                if group_id in self.config.rev_group:
                    return self.message(event, 2)
                else:
                    return self.message(event)
            else:
                if event.sub_type == "friend":
                    return self.message(event, 2)
                else:
                    return self.message(event)
        elif event.post_type == "message_sent":
            if event.msg_type == "group":
                data.past_message.append(rev)
            return self.message_sent(event)
        elif event.post_type == "notice":
            data.past_notice.append(rev)
            return self.notice(event)
        elif event.post_type == "request":
            self.past_request.append(rev)
            return self.request(event)
        elif event.post_type == "meta_event":
            return self.event(event)

    def handle_console(self, rev):
        """终端命令处理"""
        if rev:
            logger.info("%s", f"<console> {rev}")
        return ExecuteCmd(rev, self)

    def module_handle(self, event: Event, handle_type: str, auth=3):
        """具体模块处理"""
        try:
            if handle_type == "message":
                for mod in self.modules.values():
                    if mod.HANDLE_MESSAGE:
                        if mod(event, auth).success:
                            break
            elif handle_type == "message_sent":
                for mod in self.modules.values():
                    if mod.HANDLE_MESSAGE_SENT:
                        if mod(event, auth).success:
                            break
            elif handle_type == "notice":
                for mod in self.modules.values():
                    if mod.HANDLE_NOTICE:
                        if mod(event, auth).success:
                            break
            elif handle_type == "request":
                for mod in self.modules.values():
                    if mod.HANDLE_REQUEST:
                        if mod(event, auth).success:
                            break
            elif handle_type == "event":
                for mod in self.modules.values():
                    if mod.HANDLE_EVENT:
                        if mod(event, auth).success:
                            break
        except Exception:
            if not self.config.is_error_reply:
                return
            if event.group_id == "":
                reply_event(self, event, f"%FATAL_ERROR%\n{simplify_traceback(traceback.format_exc())}")
            else:
                if len(self.config.admin_list):
                    send_msg(self, "private", self.config.admin_list[0], f"%FATAL_ERROR%\n{simplify_traceback(traceback.format_exc())}")
                elif event.group_id not in self.config.rev_group:
                    return
                else:
                    reply_event(self, event, f"%FATAL_ERROR%\n{simplify_traceback(traceback.format_exc())}")

    def message(self, event: Event, auth=3):
        """处理消息事件

        Args:
            event (Event): 事件数据
            auth (int, optional): 权限等级
        """
        if not event.group_id:
            self.printf(
                f"{Fore.GREEN}[RECEIVE] {Fore.RESET}"
                f"{Fore.MAGENTA}{event.user_name}({event.user_id}){Fore.RESET}: {event.msg}"
            )
        elif event.group_id:
            if self.at_info in event.msg:
                self.printf(
                    f"{Fore.GREEN}[RECEIVE] {Fore.RESET}群"
                    f"{Fore.MAGENTA}{event.group_name}({event.group_id}){Fore.RESET}内"
                    f"{Fore.MAGENTA}{event.user_name}({event.user_id}){Fore.RESET}: {event.msg}"
                )
            elif self.config.is_show_all_msg:
                self.printf(
                    f"{Fore.GREEN}[RECEIVE] {Fore.RESET}群"
                    f"{Fore.MAGENTA}{event.group_name}({event.group_id}){Fore.RESET}内"
                    f"{Fore.MAGENTA}{event.user_name}({event.user_id}){Fore.RESET}: {event.msg}"
                )
        self.module_handle(event, "message", auth)

    def message_sent(self, event: Event, auth=3):
        """处理发送消息事件

        Args:
            event (Event): 事件数据
        """
        if self.config.is_show_all_msg:
            self.printf(
                f"{Fore.BLUE}[SENT]{Fore.RESET}发送 -> "
                f"{Fore.MAGENTA}{event.target_name}({event.target_id}){Fore.RESET} "
                f"{Fore.MAGENTA}(msg_id:{event.msg_id}){Fore.RESET} "
                f"{event.msg}"
            )
        self.module_handle(event, "message_sent", auth)

    def notice(self, event: Event, auth=3):
        """处理通知事件

        Args:
            event (Event): 事件数据
            auth (int, optional): 权限等级
        """
        self.module_handle(event, "notice", auth)

    def request(self, event: Event, auth=3):
        """处理请求事件

        Args:
            event (Event): 事件数据
            auth (int, optional): 权限等级
        """
        request_type = event.raw.get("request_type")
        comment = event.raw.get("comment")
        if request_type == "friend":
            self.printf(
                f"{Fore.CYAN}[REQUEST]{Fore.RESET}{Fore.MAGENTA}{event.user_name}({event.user_id}){Fore.RESET}发送好友请求"
                f"{Fore.MAGENTA}{comment}{Fore.RESET}，使用 {Fore.CYAN}add agree/deny 备注{Fore.RESET} 同意或拒绝此请求"
            )
        elif request_type == "group":
            self.printf(
                f"{Fore.CYAN}[REQUEST]{Fore.RESET}{Fore.MAGENTA}{event.user_name}({event.user_id}){Fore.RESET}发送加群请求"
                f"{Fore.MAGENTA}{comment}{Fore.RESET}，使用 {Fore.CYAN}add agree/deny 理由{Fore.RESET} 同意或拒绝此请求"
            )
        self.module_handle(event, "request", auth)

    def event(self, event: Event, auth=3):
        """处理元事件

        Args:
            event (Event): 事件数据
            auth (int, optional): 权限等级
        """
        if self.config.is_show_heartbeat:
            received = event.raw["status"]["stat"]["PacketReceived"]
            self.printf(f"{Fore.CYAN}[EVENT]{Fore.RESET}接收到API的第{Fore.MAGENTA}{received}{Fore.RESET}个心跳包")
        self.module_handle(event, "event", auth)

    def import_modules(self):
        """导入modules内的模块"""
        def import_classes(folder_path):
            for item in sorted(os.listdir(folder_path)):
                item_path = os.path.join(folder_path, item)
                if item.endswith(".py"):
                    module_name = os.path.splitext(item)[0]
                    missing = scan_missing_modules(item_path)
                    if missing:
                        self.errorf(f"文件({item})缺失模块: {" ".join(missing)}, 加载失败!")
                        continue
                    spec = importlib.util.spec_from_file_location(module_name, item_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    is_module = False
                    disabled = False
                    for _, obj in list(vars(module).items()):
                        if isinstance(obj, type) and hasattr(obj, "ID") and obj.ID and hasattr(obj, "NAME") and obj.NAME:
                            if obj.ID in self.config.disabled:
                                self.printf(f"[{obj.ID}] 文件({item})有效, 但已禁用, 取消加载模块!")
                                disabled = True
                                continue
                            is_module = True
                            self.module_enable(obj, item)
                            if hasattr(obj, "AUTO_INIT") and obj.AUTO_INIT:
                                obj(Event(self))
                    if not is_module and not disabled:
                        self.warnf(f"文件[{item}]内没有有效的模块, 已取消加载!")
        import_classes("modules")

    def module_enable(self, module: Module, module_file: str):
        """
        启用组件
        :param module: 组件方法
        :param module_file: 组件文件名
        """
        if module.ID in self.modules:
            self.errorf(
                f"载入失败！重名模块 {Fore.YELLOW}[{module.ID}] {module.NAME}({module_file}){Fore.RESET}"
            )
        else:
            self.modules[module.ID] = module
            self.printf(f"{Fore.CYAN}[{module.ID}] {Fore.RESET}{module.NAME}({module_file})已接入！")

    def printf(self, msg, end="\n", console=True, flush=False):
        """
        向控制台输出通知级别的消息
        :param msg: 信息
        :param end: 末尾字符
        :param console: 是否增加一行<console>
        """
        msg = handle_placeholder(str(msg), self.placeholder_dict)
        prefix = f"\r[{time.strftime("%H:%M:%S", time.localtime())} INFO] "
        if self.config.is_show_image:
            msg = msg_img2char(self.config, msg)
        if flush:
            print(msg, end=end,flush=flush)
        else:
            print(f"{prefix}{msg}", end=end, flush=flush)
        if console and not flush:
            print(f"\r{Fore.GREEN}<console> {Fore.RESET}", end="")
        logger.info("%s", format_to_log(f"{prefix}{msg}"))

    def warnf(self, msg, end="\n", console=True):
        """
        向控制台输出警告级别的消息
        :param msg: 信息
        :param end: 末尾字符
        :param console: 是否增加一行<console>
        """
        msg = handle_placeholder(str(msg), self.placeholder_dict)
        msg = msg.replace(Fore.RESET, Fore.YELLOW)
        prefix = f"\r[{time.strftime("%H:%M:%S", time.localtime())} WARN] "
        msg = f"{Fore.YELLOW}{prefix}{msg}{Fore.RESET}"
        print(msg, end=end)
        logger.info("%s", format_to_log(msg))
        if console:
            print(f"\r{Fore.GREEN}<console> {Fore.RESET}", end="")

    def errorf(self, msg, end="\n", console=True):
        """
        向控制台输出错误级别的消息
        :param msg: 信息
        :param end: 末尾字符
        :param console: 是否增加一行<console>
        """
        msg = handle_placeholder(str(msg), self.placeholder_dict)
        prefix = f"\r[{time.strftime("%H:%M:%S", time.localtime())} ERROR] "
        msg = f"{Fore.RED}{prefix}{msg}{Fore.RESET}"
        print(msg, end=end)
        logger.info("%s", format_to_log(msg))
        if console:
            print(f"\r{Fore.GREEN}<console> {Fore.RESET}", end="")
