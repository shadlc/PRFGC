"""函数库"""

import ast
import asyncio
from datetime import datetime, timedelta
import importlib
import inspect
import io
import logging
import os
import re
import html
import socket
import time
import json
import random
import traceback

from typing import TYPE_CHECKING, Callable, Dict, Optional, Set

import httpx
from PIL import Image
from colorama import Fore, Style

from src.config import Config
from src import api

if TYPE_CHECKING:
    from src.robot import Concerto

def listening(host: str, port: int, timeout: int=5) -> tuple[dict|str]:
    """监听指定地址与端口"""
    try:
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        client, _ = server.accept()
        client.settimeout(timeout)
        # client.setblocking(False)
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = client.recv(1024)
            if not chunk:
                break
            response.extend(chunk)
        header_bytes, remaining = response.split(b"\r\n\r\n", 1)
        lines = header_bytes.decode("iso-8859-1").splitlines()
        method, path, version = lines[0].split(" ", 2)
        headers = {"Method": method, "Path": path, "HTTP-Version": version}
        content_length = 0
        transfer_encoding = None
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                key, value = key.strip(), value.strip()
                headers[key] = value
                if key.lower() == "content-length":
                    content_length = int(value)
                elif key.lower() == "transfer-encoding":
                    transfer_encoding = value.lower()
        body = bytearray()
        if transfer_encoding != "chunked":
            body.extend(remaining)
            while len(body) < content_length:
                chunk = client.recv(1024)
                if not chunk:
                    break
                body.extend(chunk)
        else:
            buffer = bytearray(remaining)
            while True:
                while b"\r\n" not in buffer:
                    buffer.extend(client.recv(1024))
                line, _, buffer = buffer.partition(b"\r\n")
                chunk_size = int(line.decode("ascii"), 16)
                if chunk_size == 0:
                    while len(buffer) < 2:
                        buffer.extend(client.recv(1024))
                    buffer = buffer[2:]
                    break
                while len(buffer) < chunk_size + 2:
                    buffer.extend(client.recv(1024))
                body.extend(buffer[:chunk_size])
                buffer = buffer[chunk_size+2:]
        client.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
        body = body.decode("utf-8")
    finally:
        client.close()
        server.close()
    return headers, body

def receive_msg(robot: "Concerto"):
    body = None
    try:
        header, body = listening(robot.config.host, int(robot.config.port))
        if robot.config.is_debug and header.get("Content-Type") != "application/json":
            robot.warnf(f"收到一非JSON数据\n{body}")
            return {}
        rev_json = json.loads(body)
        return rev_json
    except OSError as e:
        robot.errorf(f"端口{robot.config.port}已被占用，程序终止！ {e}")
        robot.is_running = False
    except socket.gaierror as e:
        robot.errorf(f"绑定地址有误！ {robot.config.host} 不是一个正确的可绑定地址，程序终止！ {e}")
        robot.is_running = False
    except json.JSONDecodeError as e:
        robot.warnf(f"{body} JSON数据解析失败！ {traceback.format_exc()}")
        return {}

def import_json(file: str):
    """导入json"""
    try:
        content = "{}"
        if not os.path.exists(file):
            open(file, "w", encoding="utf-8").write("{}")
        if temp := open(file, "r", encoding="utf-8").read():
            content = temp
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise e

def save_json(file_name: str, data: str):
    """导出json"""
    json.dump(
        data, open(file_name, "w", encoding="utf-8"), indent=2, ensure_ascii=False
    )

def merge(d1: dict, d2: dict) -> dict:
    """简单字典合并"""
    result = d1.copy()
    for key, value in d2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result

def apply_formatter(logger: logging.Logger, mid: str):
    """给传入的 logger 应用彩色格式化器"""
    class ColorFormatter(logging.Formatter):
        COLORS = {
            logging.DEBUG: Fore.BLUE,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
        }

        def format(self, record):
            color = self.COLORS.get(record.levelno, "")
            reset = Style.RESET_ALL
            record.asctime = f"{color}{record.levelname}{reset}"
            record.levelname = f"{color}{record.levelname}{reset}"
            record.msg = f"{color}{record.msg}{reset}"
            return super().format(record)
    fmt = f"\r[%(asctime)s %(levelname)s] {Fore.CYAN}[{mid}]{Fore.RESET} %(message)s"
    fmt += f"\n\r{Fore.GREEN}<console> {Fore.RESET}"
    formatter = ColorFormatter(fmt=fmt, datefmt="%H:%M:%S")
    logger.propagate = False
    if len(logger.handlers) == 0:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.terminator = ""
        logger.addHandler(ch)
    else:
        logger.handlers[0].terminator = ""
        logger.handlers[0].setFormatter(formatter)
    return logger

def calc_size(byte: int):
    """
    格式化文件大小
    :param byte: 字节数
    :return: 格式化文件大小
    """
    symbols = ("KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    prefix = dict()
    for a, s in enumerate(symbols):
        prefix[s] = 1 << (a + 1) * 10
    for s in reversed(symbols):
        if int(byte) >= prefix[s]:
            value = float(byte) / prefix[s]
            return "%.2f%s" % (value, s)
    return ".%sB" % byte

def char_colorama(char: str, rgb: list):
    """
    为字符添加标准8色
    :param char: 字符
    :param rgb: (R, G, B) 取值 0–255
    :return: 彩色字符（Standard 8 色）
    """
    R, G, B = rgb
    max_c = max(R, G, B)
    min_c = min(R, G, B)
    diff = max_c - min_c
    if diff <= 50:
        return char
    color = ""
    if R == max_c:
        if G > B:
            color = Fore.YELLOW
        elif B > G:
            color = Fore.MAGENTA
        else:
            color = Fore.RED
    elif G == max_c:
        if R > B:
            color = Fore.YELLOW
        elif B > R:
            color = Fore.CYAN
        else:
            color = Fore.GREEN
    elif B == max_c:
        if R > G:
            color = Fore.MAGENTA
        elif G > R:
            color = Fore.BLUE
        else:
            color = Fore.BLUE
    return color + char + Fore.RESET

def char_ansi_256(char: str, rgb: list):
    """
    使用 ANSI 256 色 输出字符
    :param char: 字符
    :param rgb: (R, G, B) 取值 0–255
    :return: 彩色字符（ANSI 256 色）
    """
    r, g, b = [x / 255.0 for x in rgb]
    r_ = int(r * 5)
    g_ = int(g * 5)
    b_ = int(b * 5)
    color_code = 16 + 36 * r_ + 6 * g_ + b_
    return f"\033[38;5;{color_code}m{char}\033[0m"

def char_true_color(char: str, rgb: list):
    """
    使用 TrueColor 输出字符
    :param char: 字符
    :param rgb: (R, G, B) 取值 0–255
    :return: 彩色字符（24bit）
    """
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m{char}\033[0m"

def msg_img2char(config: Config, msg: str):
    """
    检测CQ码中有图片并转化为字符画
    :param msg: 收到的消息
    :param color: 是否渲染颜色
    :return: 转化为字符画的消息
    """
    if "[RECEIVE]" not in msg:
        return msg
    matches = re.findall(r"(\[CQ:image.*?url=([^,]*).*\])", msg)
    for cq, url in matches:
        try:
            data = httpx.Client().get(url, timeout=3)
            img = Image.open(io.BytesIO(data.content)).convert("RGB")
            w, h = img.size
            ratio = h / float(w)
            target_w = sorted([config.min_image_width, w, config.max_image_width])[1]
            target_h = int(target_w * ratio * 0.5)
            img = img.resize((target_w, target_h))
            pixels = img.getdata()
            char = ""
            row = 0
            for i in pixels:
                pixel_gray = (i[0] * 38 + i[1] * 75 + i[2] * 15) >> 7
                if config.image_color == "colorama":
                    image_ascii = list(".,:;+*?#%@")
                    unit = (256 + 1) / len(image_ascii)
                    single_char = image_ascii[int(pixel_gray // unit)]
                    char += char_colorama(single_char, i)
                elif config.image_color == "ansi_256":
                    char += char_ansi_256("█", i)
                elif config.image_color == "true_color":
                    char += char_true_color("█", i)
                else:
                    image_ascii = list(".,:;+*?#%@")
                    unit = (256 + 1) / len(image_ascii)
                    single_char = image_ascii[int(pixel_gray // unit)]
                    char += single_char
                row += 1
                if row >= target_w:
                    row = 0
                    char += "\n"
            msg = msg.replace(cq, "\n" + char)
        except Exception:
            if config.is_debug:
                traceback.print_exc()
            return msg
    return msg

def status_ok(response: dict):
    """
    检测API接口是否返回正常
    :param respond: API返回的json信息
    :return: 此接口是否正常执行
    """
    if response and response.get("status") == "ok":
        return True
    else:
        return False

def handle_placeholder(text: str, placeholder_dict: dict):
    """替换标记的字符串"""
    pattern = re.compile(r"(%\S+?%)")
    flags = pattern.findall(str(text))
    for flag in flags:
        if flag.replace("%", "") in placeholder_dict:
            result_list = placeholder_dict[flag.replace("%", "")]
            text = re.sub(flag, random.choice(result_list), str(text))
            text = handle_placeholder(text, placeholder_dict)
    return text

def build_msg(text: str):
    """生成一个消息节点"""
    data = {
            "type": "text",
            "data": {
                "text": text
            }
        }
    return data

def build_node(*args, **kwargs):
    """
    生成一个转发节点
    user_id,nickname,content
    """
    content = list(args) if args else []
    if isinstance(content, list) and len(content) == 1:
        content = content[0]
    data = {
            "type": "node",
            "data": {
                "user_id": kwargs.get("user_id", "0"),
                "nickname": kwargs.get("nickname", ""),
                "content": content
            }
        }
    return data

def build_forward(text: str, user_id: str):
    """生成一个聊天记录节点"""
    data = {
            "type": "forward",
            "data": {
                "id": user_id,
                "content": text
            }
        }
    return data

def reply_event(robot: "Concerto", event: "Event", msg: str, reply=False, force=False):
    """
    快捷回复消息
    :param robot: 机器人类
    :param event: 接收到的消息事件
    :param msg: 发送的消息内容
    :param force: 无视静默模式发送消息
    :return: 发送消息后返回的json信息
    """
    msg = handle_placeholder(str(msg), robot.placeholder_dict)
    if reply:
        msg = f"[CQ:reply,id={event.msg_id}]{msg}"
    simple_msg = re.sub(r"\[CQ:(.*?),file=base64.*\]", r"[CQ:\1,file=Base64]", msg)
    if event.post_type == "message" and (not robot.config.is_silence or force):
        if event.msg_type == "group":
            group_id = event.group_id
            group_name = get_group_name(robot, group_id)
            robot.printf(
                f"{Fore.GREEN}[SEND] {Fore.RESET}向群{Fore.MAGENTA}{group_name}({group_id}){Fore.RESET}发送消息：{simple_msg}"
            )
            resp_dict = {"msg_type": "group", "number": group_id, "msg": msg}
            return api.send_msg(robot, resp_dict)
        else:
            user_id = event.user_id
            user_name = get_user_name(robot, user_id)
            robot.printf(
                f"{Fore.GREEN}[SEND] {Fore.RESET}向{Fore.MAGENTA}{user_name}({user_id}){Fore.RESET}发送消息：{simple_msg}"
            )
            resp_dict = {"msg_type": "private", "number": user_id, "msg": msg}
            return api.send_msg(robot, resp_dict)

def reply_id(robot: "Concerto", msg_type: str, uid: str, msg: str, force=False):
    """
    按id回复消息
    :param robot: 机器人类
    :param msg_type: 发送类型 group,private
    :param uid: 发送的对象id
    :param msg: 发送的消息内容
    :return: 发送消息后返回的json信息
    """
    msg = handle_placeholder(str(msg), robot.placeholder_dict)
    simple_msg = re.sub(r"\[CQ:(.*?),file=base64.*\]", r"[CQ:\1,file=Base64]", msg)
    if not robot.config.is_silence or force:
        if msg_type == "group":
            robot.printf(
                f"{Fore.GREEN}[SEND] {Fore.RESET}向群{Fore.MAGENTA}{get_group_name(robot, uid)}({uid}){Fore.RESET}发送消息：{simple_msg}"
            )
            resp_dict = {"msg_type": "group", "number": uid, "msg": msg}
            return api.send_msg(robot, resp_dict)
        else:
            robot.printf(
                f"{Fore.GREEN}[SEND] {Fore.RESET}向{Fore.MAGENTA}{get_user_name(robot, uid)}({uid}){Fore.RESET}发送消息：{simple_msg}"
            )
            resp_dict = {"msg_type": "private", "number": uid, "msg": msg}
            return api.send_msg(robot, resp_dict)

def reply_back(robot: "Concerto", owner_id: str, msg: str):
    """
    对reply_id方法的封装，对owner_id发送消息
    :param robot: 机器人类
    :param owner_id: 用户识别ID
    :param msg: 发送的消息内容
    """
    if owner_id[:1] == "u":
        reply_id(robot, "private", owner_id[1:], msg)
    else:
        reply_id(robot, "group", owner_id[1:], msg)

def quick_reply(robot: "Concerto", raw: dict, msg: str):
    """
    调用“.handle_quick_operation”接口的快捷回复消息
    :param robot: 机器人类
    :param raw: 接收到的消息json信息
    :param msg: 发送的消息内容
    :return: 发送消息后返回的json信息
    """
    msg = handle_placeholder(str(msg), robot.placeholder_dict)
    if raw["post_type"] == "message":
        robot.self_message.append(
            {
                "message": msg,
                "message_id": "查阅API端",
                "message_type": raw["message_type"],
                "user_id": robot.self_id,
                "time": time.time(),
            }
        )
        resp_dict = {"context": raw, "operation": {"reply": msg}}
        return api.handle_quick_operation(robot, resp_dict)

def send_msg(robot: "Concerto", msg_type: str, number: str, msg: str, group_id: str=None):
    """
    发送消息
    :param robot: 机器人类
    :param msg_type: 消息类型
    :param number: 对方ID
    :param msg: 消息内容
    :return: 消息内容
    """
    msg = handle_placeholder(str(msg), robot.placeholder_dict)
    resp_dict = {"msg_type": msg_type, "number": number, "msg": msg, "group_id": group_id}
    result = api.send_msg(robot, resp_dict)
    if status_ok(result):
        resp_dict = {"message_id": result["data"]["message_id"]}
        robot.self_message.append(api.get_msg(robot, resp_dict)["data"])
    return result

def get_msg(robot: "Concerto", msg_id: str):
    """
    获取消息内容
    :param robot: 机器人类
    :param msg_id: 消息ID
    :return: 消息内容
    """
    resp_dict = {"message_id": msg_id}
    return api.get_msg(robot, resp_dict)

def del_msg(robot: "Concerto", msg_id: str):
    """
    撤回消息
    :param robot: 机器人类
    :param msg_id: 消息ID
    """
    resp_dict = {"message_id": msg_id}
    return api.del_msg(robot, resp_dict)

def get_forward_msg(robot: "Concerto", msg_id: str):
    """
    获取转发消息内容
    :param robot: 机器人类
    :param msg_id: 转发消息ID
    :return: 转发消息内容
    """
    if msg_id == 0:
        return None
    resp_dict = {"message_id": msg_id}
    return api.get_forward_msg(robot, resp_dict)

def send_forward_msg(robot: "Concerto", nodes: list, group_id=None, user_id=None, source=None, hidden=False):
    """
    发送转发消息
    :param robot: 机器人类
    :param node: 转发消息内容物
    :param group_id: 发送到群ID
    :param user_id: 发送到用户ID
    :param source: 来源字段
    :return: 发送消息后返回的json信息
    """
    data = {"messages": nodes, "source": source}
    if group_id:
        data["group_id"] = group_id
    elif user_id:
        data["user_id"] = user_id
    else:
        return
    if hidden:
        data["news"] = []
    result = api.post(robot, "/send_forward_msg", data)
    if status_ok(result):
        robot.self_message.append(
            get_msg(robot, result["data"]["message_id"])["data"]
        )
    return result


def send_private_forward_msg(robot: "Concerto", node: dict, user_id: str):
    """
    发送私聊转发消息
    :param robot: 机器人类
    :param node: 转发消息内容物
    :param user_id: 发送到的用户ID
    :return: 发送消息后返回的json信息
    """
    data = {"user_id": user_id, "messages": node}
    result = api.post(robot, "/send_private_forward_msg", data)
    if status_ok(result):
        robot.self_message.append(
            get_msg(robot, result["data"]["message_id"])["data"]
        )
    return result

def send_group_forward_msg(robot: "Concerto", node: dict, group_id: str):
    """
    发送群聊转发消息
    :param robot: 机器人类
    :param group_id: 发送到群ID
    :param node: 转发消息内容物
    :return: 发送消息后返回的json信息
    """
    data = {"group_id": group_id, "messages": node}
    result = api.post(robot, "/send_group_forward_msg", data)
    if status_ok(result):
        robot.self_message.append(
            get_msg(robot, result["data"]["message_id"])["data"]
        )
    return result

def get_group_msg_history(robot: "Concerto", group_id: str):
    """
    获取群消息历史
    :param robot: 机器人类
    :param group_id: 群ID
    :return: 消息json信息
    """
    resp_dict = {"group_id": group_id}
    return api.get_group_msg_history(robot, resp_dict)

def reply_add(robot: "Concerto", raw: dict, accept: str, msg: str):
    """
    回复添加请求
    :param robot: 机器人类
    :param raw: 接收到的请求json信息
    :param accept: 是否接受
    :param msg: 操作理由
    :return: 发送消息后返回的json信息
    """
    if raw["post_type"] == "request":
        return api.handle_quick_operation(robot,
            {
                "context": raw,
                "operation": {"approve": accept, "remark": msg, "reason": msg},
            }
        )

def get_user_name(robot: "Concerto", uid: str):
    """
    获取用户信息
    :param robot: 机器人类
    :param uid: 用户ID
    :return: 用户信息
    """
    if not uid:
        return
    uid = str(uid)
    if uid in robot.user_dict:
        return robot.user_dict[uid]
    else:
        resp_dict = {"user_id": uid}
        result = api.get_stranger_info(robot, resp_dict)
        if status_ok(result):
            name = result["data"]["nickname"]
            robot.user_dict[uid] = name
            return name
        return ""

def get_group_info(robot: "Concerto", group_id: str):
    """
    获取群信息
    :param robot: 机器人类
    :param id: 群号
    :return: 群信息
    """
    resp_dict = {"group_id": group_id}
    return api.get_group_info(robot, resp_dict)

def set_group_ban(robot: "Concerto", group_id: str, user_id: str, duration: int):
    """
    设置群禁言
    :param robot: 机器人类
    :param group_id: 群号
    :param user_id: 用户
    :param duration: 时长
    """
    resp_dict = {"group_id": int(group_id), "user_id": int(user_id), "duration": int(duration)}
    return api.set_group_ban(robot, resp_dict)

def set_group_whole_ban(robot: "Concerto", group_id: str, enable: bool):
    """
    设置群禁言
    :param robot: 机器人类
    :param group_id: 群号
    :param user_id: 用户
    :param duration: 时长
    """
    resp_dict = {"group_id": int(group_id), "enable": enable}
    return api.set_group_whole_ban(robot, resp_dict)

def set_group_kick(robot: "Concerto", group_id: str, user_id: str):
    """
    设置群禁言
    :param robot: 机器人类
    :param group_id: 群号
    :param user_id: 用户
    """
    resp_dict = {"group_id": int(group_id), "user_id": int(user_id)}
    return api.set_group_kick(robot, resp_dict)

def get_group_name(robot: "Concerto", group_id: str):
    """
    获取群名称
    :param robot: 机器人类
    :param id: 群号
    """
    if not group_id:
        return
    group_id = str(group_id)
    if group_id in robot.group_dict:
        return robot.group_dict[group_id]
    else:
        result = get_group_info(robot, group_id)
        if status_ok(result):
            name = result["data"]["group_name"]
            robot.group_dict[group_id] = name
            return name
        else:
            return ""

def get_image(robot: "Concerto", file: str):
    """
    获取图片
    :param robot: 机器人类
    :param file: 文件的标识码
    :return: 文件下载链接
    """
    resp_dict = {"file": file}
    return api.get_image(robot, resp_dict)

def poke(robot: "Concerto", user_id: str, group_id=""):
    """
    戳一戳
    :param robot: 机器人类
    :param user_id: 用户ID
    :param group_id: 群ID
    """
    resp_dict = {"user_id": user_id, "group_id": group_id}
    if group_id:
        return api.group_poke(robot, resp_dict)
    else:
        return api.friend_poke(robot, resp_dict)

def set_model_show(robot: "Concerto", device: str, model_show: str):
    """
    贴表情
    :param robot: 机器人类
    :param device: 设备名
    :param model_show: 展示名称
    """
    resp_dict = {"model": device, "model_show": model_show}
    return api.set_model_show(robot, resp_dict)

def set_emoji(robot: "Concerto", message_id: str, emoji_id: str, is_set=True):
    """
    贴表情
    :param robot: 机器人类
    :param message_id: 消息ID
    :param set: 贴上/取下
    """
    resp_dict = {"message_id": message_id, "emoji_id": emoji_id, "set": is_set}
    return api.set_msg_emoji_like(robot, resp_dict)

def group_sign(robot: "Concerto", group_id: str):
    """
    贴表情
    :param robot: 机器人类
    :param group_id: 群ID
    """
    resp_dict = {"group_id": group_id}
    return api.set_group_sign(robot, resp_dict)

def send_group_notice(robot: "Concerto", group_id: str, notice: str):
    """
    发送群公告
    :param robot: 机器人类
    :param group_id: 群ID
    :param notice: 群公告内容
    """
    resp_dict = {"group_id": group_id, "content": notice}
    return api.send_group_notice(robot, resp_dict)

def send_like(robot: "Concerto", user_id: str, times: int):
    """
    贴表情
    :param robot: 机器人类
    :param user_id: 用户ID
    :param times: 次数
    """
    resp_dict = {"user_id": user_id, "times": times}
    return api.send_like(robot, resp_dict)

def send_group_ai_record(robot: "Concerto", group_id: str, character: str, text: str):
    """
    发送群AI语音
    :param robot: 机器人类
    :param group_id: 群ID
    :param character: AI音色
    :param text: 文本
    """
    resp_dict = {"group_id": group_id, "character": character, "text": text}
    return api.send_group_ai_record(robot, resp_dict)

def group_member_info(robot: "Concerto", group_id: str, user_id: str):
    """
    获取群成员信息
    :param robot: 机器人类
    :param group_id: 群ID
    :param user_id: 用户ID
    """
    resp_dict = {"group_id": group_id, "user_id": user_id}
    return api.get_group_member_info(robot, resp_dict)

def group_special_title(robot: "Concerto", group_id: str, user_id: str, special_title: str):
    """
    设置群成员专属头衔
    :param robot: 机器人类
    :param group_id: 群ID
    """
    resp_dict = {"group_id": group_id, "user_id": user_id, "special_title": special_title}
    return api.set_group_special_title(robot, resp_dict)

def get_stranger_info(robot: "Concerto", user_id: int):
    """
    获取用户信息
    :param robot: 机器人类
    :param group_id: 群ID
    """
    resp_dict = {"user_id": user_id}
    return api.get_stranger_info(robot, resp_dict)

def ocr_image(robot: "Concerto", img_id: str):
    """
    OCR图片识别
    :param robot: 机器人类
    :param img_id: 消息ID
    """
    resp_dict = {"image": img_id}
    return ocr_image(robot, resp_dict)

def simplify_traceback(tb: str):
    """
    获取错误报告并简化
    :param tb: 获取的错误报告
    :return: 易读的错误报告
    """
    result = "按从执行顺序排序有\n"
    tb = tb.strip().split("\n")
    exclude = True
    for excepts in tb[1:]:
        if exclude and "__init__" not in excepts:
            continue
        exclude = False
        if re.search(r"(\\|/)(\w*?\.py).*line\s([0-9]+).*in\s(.*)", excepts):
            temp = re.search(
                r"(\\|/)(\w*?\.py).*line\s([0-9]+).*in\s(.*)", excepts
            ).groups()
            result += f"文件{temp[1]}中第{temp[2]}行的“{temp[3]}”方法出错\n"
    result += f"导致最终错误为“{tb[-1]}”"
    return result

def get_error():
    """
    获取错误原因
    :return: 直接的错误原因
    """
    return traceback.format_exc().strip().rsplit("\n", maxsplit=1)[-1]

def scan_missing_modules(file_path: str):
    """
    扫描单个py文件返回缺失模块列表
    """
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)
    missing = set()
    optional = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                if isinstance(stmt, ast.Import):
                    for alias in stmt.names:
                        optional.add(alias.name.split(".")[0])
                elif isinstance(stmt, ast.ImportFrom) and stmt.module:
                    optional.add(stmt.module.split(".")[0])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split(".")[0]
                if module_name not in optional:
                    try:
                        importlib.import_module(module_name)
                    except ModuleNotFoundError as e:
                        missing.add(e.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split(".")[0]
                if module_name not in optional:
                    try:
                        importlib.import_module(module_name)
                    except ModuleNotFoundError as e:
                        missing.add(e.name)
    return missing

def via(condition, success=True):
    """模块方法装饰器"""
    def decorator(func):
        async def wrapper(self: "Module", *args, **kwargs):
            if condition(self):
                if self.robot.config.is_debug:
                    self.printf(f"执行{Fore.YELLOW}[{func.__name__}]{Fore.RESET}方法")
                try:
                    self.success = success
                    if inspect.iscoroutinefunction(func):
                        return await func(self, *args, **kwargs)
                    else:
                        return func(self, *args, **kwargs)
                except Exception:
                    self.errorf(f"{Fore.RED}执行{Fore.YELLOW}[{self.ID}.{func.__name__}]{Fore.RED}方法发生错误！")
                    self.errorf(Fore.RED + traceback.format_exc())
                    self.success = False
                    raise
            # else:
            #     self.robot.printf(f"未满足[{self.ID}.{func.__name__}]的条件")
        wrapper._method = True # pylint: disable=protected-access
        return wrapper
    return decorator

class MiniCron:
    """简单的Crontab""" 
    def __init__(self, expr: str, task: Callable[[], None]) -> None:
        """
        expr: crontab 表达式 (如 "0 8 * * *")
        task: 要执行的函数，无参数，无返回值
        """
        self.expr: str = expr
        self.task: Callable[[], None] = task
        self.cron_fields: Dict[str, Set[int]] = self._parse_cron(expr)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        """解析单个字段，返回允许的整数集合"""
        if field == "*":
            return set(range(min_val, max_val + 1))
        values: Set[int] = set()
        for part in field.split(","):
            if part.startswith("*/"):  # */n
                step = int(part[2:])
                values.update(range(min_val, max_val + 1, step))
            elif "-" in part:
                start, end = map(int, part.split("-"))
                values.update(range(start, end + 1))
            else:
                values.add(int(part))
        return values

    def _parse_cron(self, expr: str) -> Dict[str, Set[int]]:
        """解析 cron 表达式，返回每个字段允许的整数集合"""
        minute, hour, day, month, weekday = expr.split()
        return {
            "minute": self._parse_field(minute, 0, 59),
            "hour": self._parse_field(hour, 0, 23),
            "day": self._parse_field(day, 1, 31),
            "month": self._parse_field(month, 1, 12),
            "weekday": self._parse_field(weekday, 0, 6),  # 0=周一 … 6=周日
        }

    def _next_time(self, from_time: Optional[datetime] = None) -> datetime:
        """计算下一个匹配 cron 表达式的时间点"""
        if from_time is None:
            from_time = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=1)
        else:
            from_time = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

        while True:
            if (from_time.minute in self.cron_fields["minute"] and
                from_time.hour in self.cron_fields["hour"] and
                from_time.day in self.cron_fields["day"] and
                from_time.month in self.cron_fields["month"] and
                from_time.weekday() in self.cron_fields["weekday"]):
                return from_time
            from_time += timedelta(minutes=1)

    async def run(self) -> None:
        """开始循环执行任务"""
        next_run: datetime = self._next_time()
        while True:
            now: datetime = datetime.now()
            if now >= next_run:
                self.task()
                next_run = self._next_time(now)
            else:
                await asyncio.sleep((next_run - now).total_seconds())

class Event:
    """基础事件结构"""  
    def __init__(self, robot: "Concerto", raw = None):
        # 机器人本类
        self.robot = robot
        # 原始数据结构
        self.raw = raw = raw or {}
        # 上报类型 message消息 notice系统提示 request请求
        self.post_type = raw.get("post_type", "")
        # 事件发生的时间戳
        self.time = raw.get("time", "")
        # 机器人自身QQ号
        self.self_id = str(raw.get("self_id", ""))
        # 消息类型 private私聊 group群聊
        self.msg_type = raw.get("message_type", "")
        # 通知类型 notify常用通知 essence群精华消息 group_upload群文件上传 group_admin群变动 group_decrease群成员减少 group_increase群成员增加 group_ban群禁言 friend_add好友添加 group_recall群消息撤回 friend_recall好友消息撤回 group_card群成员名片更新 offline_file离线文件 client_status客户端状态变更
        self.notice_type = raw.get("notice_type", "")
        # 消息子类型 friend好友 group群临时会话 group_self群聊 other其他 normal普通 anonymous匿名 notice系统提示
        self.sub_type = raw.get("sub_type", "")
        # 消息 ID
        self.msg_id = raw.get("message_id", "")
        # 原始消息内容
        self.msg = html.unescape(raw.get("message", ""))
        if "CQ:json" in self.msg:
            self.msg = re.sub(r"(\s)+", "", self.msg)
        # 发送者ID
        self.sender_id = str(raw.get("sender_id", ""))
        # 发送者QQ号
        self.user_id = str(raw.get("user_id", ""))
        # 发送者名称
        self.user_name = raw.get("sender", {}).get("nickname", "")
        if self.user_name == "" and self.user_id.isdigit():
            self.user_name = get_user_name(robot, self.user_id)
        # 发送者昵称
        self.user_card = raw.get("sender", {}).get("card", "")
        # 群号
        self.group_id = str(raw.get("group_id", ""))
        if self.group_id == "0":
            self.group_id = ""
        # 群名
        self.group_name = get_group_name(robot, self.group_id)
        # 目标QQ号
        self.target_id = str(raw.get("target_id", ""))
        # 目标昵称
        self.target_name = get_user_name(robot, self.target_id) if self.msg_type == "private" else get_group_name(robot, self.group_id)
        # 操作者QQ号
        self.operator_id = str(raw.get("operator_id", ""))
        # 操作者昵称
        self.operator_name = get_user_name(robot, self.operator_id)
        self.operator_nick = raw.get("operator_nick", "")

class Module:
    """模块基类"""
    ID = None
    NAME = None
    HELP = None
    CONFIG = None
    GLOBAL_CONFIG = None
    CONV_CONFIG = None
    AUTO_INIT = None

    HANDLE_MESSAGE = True
    HANDLE_MESSAGE_SENT = False
    HANDLE_NOTICE = False
    HANDLE_REQUEST = False
    HANDLE_META_EVENT = False

    def __init__(self, event: Event, auth: int=0):
        self.name = self.__class__.NAME
        self.success = False
        self.event = event
        self.robot = event.robot
        self.auth = int(auth)
        self.owner_id = ""
        self.config_file = ""
        self.config = {}
        self.data = {}
        self.init_config()
        if not self.premise():
            return
        asyncio.run_coroutine_threadsafe(self.activate(), self.robot.loop)

    def premise(self):
        """前置条件"""
        return True

    async def activate(self):
        """执行类方法"""
        for attr_name in dir(self):
            func = getattr(self, attr_name)
            if not self.success and callable(func) and getattr(func, "_method", False):
                await func()

    def au(self, max_level=3, min_level=0):
        """检查权限等级"""
        return min_level <= self.auth <= max_level

    def group_at(self):
        """仅群聊@消息触发"""
        return self.robot.at_info in self.event.msg

    def at_or_private(self):
        """群聊@消息以及私聊消息触发"""
        return self.event.group_id == "" or self.robot.at_info in self.event.msg

    def start_with_sign(self):
        """开头#触发"""
        return re.search(r"^#\S+", self.event.msg)

    def match(self, pattern: str):
        """消息规则匹配"""
        msg = self.event.msg.replace(self.robot.at_info, "").strip()
        return re.search(pattern, msg)

    def is_self_send(self):
        """判断是不是自己发送的数据"""
        return self.robot.self_id in [self.event.user_id, self.event.sender_id]

    def go_on(self):
        """未成功执行该模块"""
        self.success = False

    def init_config(self):
        """初始化模块数据"""
        # 初始化配置
        if self.CONFIG is None:
            return
        self.config_file = os.path.join(self.robot.config.data_path, self.CONFIG)
        try:
            self.config = import_json(self.config_file)
        except Exception:
            self.config = {}
            self.errorf(f"配置文件 {self.config_file} 解析发生错误!\n{traceback.format_exc()}")
        self.GLOBAL_CONFIG = self.GLOBAL_CONFIG or {}
        self.config = merge(self.GLOBAL_CONFIG, self.config)
        self.save_config()
        # 设定会话的owner_id
        if self.event.group_id:
            self.owner_id = f"g{self.event.group_id}"
        elif self.event.user_id:
            self.owner_id = f"u{self.event.user_id}"
        else:
            self.owner_id = f"u{self.robot.self_id}"
        # 读取指定会话的数据与配置文件
        self.data = self.robot.data.get(self.owner_id)
        if self.CONV_CONFIG is None:
            return
        if self.owner_id not in self.config:
            self.config[self.owner_id] = {}
        self.CONV_CONFIG = self.CONV_CONFIG or {}
        self.config[self.owner_id] = merge(self.CONV_CONFIG, self.config[self.owner_id])
        self.save_config()

    def save_config(self, config_content=None, owner_id=""):
        """保存模块配置"""
        if owner_id and config_content:
            self.config[owner_id] = config_content
        elif config_content:
            self.config = config_content
        try:
            save_json(self.config_file, self.config)
        except Exception:
            self.errorf(f"配置文件 {self.config_file} 保存失败!\n{traceback.format_exc()}")

    def reply(self, msg, reply=False, force=False):
        """快捷回复消息"""
        if self.robot.config.is_always_reply:
            reply = True
        return reply_event(self.robot, self.event, msg, reply=reply, force=force)

    def reply_forward(self, nodes: list, source=None, hidden=True):
        """快捷回复转发消息"""
        if self.event.group_id:
            send_forward_msg(self.robot, nodes, group_id=self.event.group_id, source=source, hidden=hidden)
        else:
            send_forward_msg(self.robot, nodes, user_id=self.event.user_id, source=source, hidden=hidden)

    def printf(self, msg, end="\n", console=True, flush=False):
        """
        向控制台输出通知级别的消息
        :param msg: 信息
        :param end: 末尾字符
        :param console: 是否增加一行<console>
        """
        if not flush:
            msg = f"{Fore.CYAN}[{self.ID}]{Fore.RESET} {msg}"
        self.robot.printf(msg=msg, end=end, console=console, flush=flush)

    def warnf(self, msg, end="\n", console=True):
        """
        向控制台输出警告级别的消息
        :param msg: 信息
        :param end: 末尾字符
        :param console: 是否增加一行<console>
        """
        self.robot.warnf(f"{Fore.CYAN}[{self.ID}]{Fore.YELLOW} {msg}", end=end, console=console)

    def errorf(self, msg, end="\n", console=True):
        """
        向控制台输出错误级别的消息
        :param msg: 信息
        :param end: 末尾字符
        :param console: 是否增加一行<console>
        """
        self.robot.errorf(f"{Fore.CYAN}[{self.ID}]{Fore.RED} {msg}", end=end, console=console)
