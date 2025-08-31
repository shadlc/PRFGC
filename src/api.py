"""API定义"""

import json
import time

from typing import TYPE_CHECKING

from colorama import Fore
import httpx

if TYPE_CHECKING:
    from robot import Concerto

def get(robot: "Concerto", url):
    """GET请求"""
    try:
        get_url = robot.config.api_base + url
        robot.request_list.append(f"GET{url}")
        data = httpx.Client().get(get_url, timeout=30)
        rev_json = data.json()
        if robot.config.is_debug:
            robot.printf(f"{Fore.YELLOW}[DATA]{Fore.RESET} GET请求{Fore.MAGENTA}[{get_url}]{Fore.RESET}后返回{Fore.YELLOW}{rev_json}{Fore.RESET}")
        return rev_json
    except httpx.DecodingError:
        robot.errorf("数据解析错误！")
        return {}
    except httpx.InvalidURL:
        robot.errorf("无效的请求地址！")
        return {}

def post(robot: "Concerto", url, data):
    """POST请求"""
    try:
        data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        post_url = robot.config.api_base + url
        robot.request_list.append(f"POST{url} | {data}")
        header = {"Content-Type": "application/json"}
        data = httpx.Client().post(post_url, headers=header, data=data, timeout=30)
        rev_json = data.json()
        if robot.config.is_debug:
            robot.printf(f"{Fore.YELLOW}[DATA]{Fore.RESET} POST请求{Fore.MAGENTA}[{post_url}]{Fore.RESET}后返回{Fore.YELLOW}{rev_json}{Fore.RESET}")
        return rev_json
    except httpx.DecodingError:
        robot.errorf("数据解析错误！")
        return {}
    except httpx.InvalidURL:
        robot.errorf("无效的请求地址！")
        return {}

def send_msg(robot: "Concerto", resp: dict):
    msg_type = resp.get("msg_type")  # 回复类型（群聊/私聊）
    number = resp.get("number")  # 回复账号（群号/好友号）
    group_id = resp.get("group_id")  # 临时会话群号（群号）
    msg = str(resp.get("msg"))  # 要回复的消息
    if msg_type == "group":
        url = "/send_group_msg"
        data = {"group_id": str(number), "message": msg}
    elif msg_type == "private":
        url = "/send_private_msg"
        data = {"user_id": str(number), "group_id": str(group_id), "message": msg}
    else:
        url = ""
        data = ""
    result = post(robot, url, data)
    return result

def del_msg(robot: "Concerto", resp: dict):
    message_id = resp["message_id"]  # 消息ID
    url = "/delete_msg?message_id=" + str(message_id)
    return get(robot, url)

def get_msg(robot: "Concerto", resp: dict):
    message_id = resp["message_id"]  # 消息ID
    url = "/get_msg?message_id=" + str(message_id)
    return get(robot, url)

def get_forward_msg(robot: "Concerto", resp: dict):
    return post(robot, "/get_forward_msg", resp)

def send_group_notice(robot: "Concerto", resp: dict):
    group_id = resp["group_id"]  # 群号
    content = resp["content"]  # 公告内容
    url = "/_send_group_notice?group_id=" + str(group_id) + "&content=" + content
    return get(robot, url)

def send_group_ai_record(robot: "Concerto", resp: dict):
    return post(robot, "/send_group_ai_record", resp)

def get_image(robot: "Concerto", resp: dict):
    file = resp["file"]  # 图片缓存文件名
    url = "/get_image?file=" + str(file)
    return get(robot, url)

def handle_quick_operation(robot: "Concerto", resp: dict):
    context = resp["context"]  # 事件数据对象
    operation = resp["operation"]  # 快速操作对象
    url = "/.handle_quick_operation"
    operation = {"context": context, "operation": operation}
    return post(robot, url, operation)

def ocr_image(robot: "Concerto", resp: dict):
    image = resp["image"]  # 图片ID
    url = "/.ocr_image?image=" + image
    return get(robot, url)

def upload_private_file(robot: "Concerto", resp: dict):
    user_id = resp["user_id"]  # 用户ID
    file = resp["file"]  # 本地目录
    name = resp["name"]  # 文件名称
    url = (
        "/upload_private_file?group_id="
        + str(user_id)
        + "&file="
        + file
        + "&name="
        + name
    )
    return get(robot, url)

def upload_group_file(robot: "Concerto", resp: dict):
    group_id = resp["group_id"]  # 群号
    file = resp["file"]  # 本地目录
    name = resp["name"]  # 文件名称
    url = (
        "/upload_group_file?group_id="
        + str(group_id)
        + "&file="
        + file
        + "&name="
        + name
    )
    return get(robot, url)

def get_group_msg_history(robot: "Concerto", resp: dict):
    url = "/get_group_msg_history"
    return post(robot, url, resp)

def get_stranger_info(robot: "Concerto", resp: dict):
    user_id = resp["user_id"]  # 目标QQ号
    url = "/get_stranger_info?user_id=" + str(user_id)
    return get(robot, url)

def get_group_info(robot: "Concerto", resp: dict):
    group_id = resp["group_id"]  # 目标群号
    url = "/get_group_info?group_id=" + str(group_id)
    return get(robot, url)

def set_group_ban(robot: "Concerto", resp: dict):
    url = "/set_group_ban"
    return post(robot, url, resp)

def set_group_whole_ban(robot: "Concerto", resp: dict):
    url = "/set_group_whole_ban"
    return post(robot, url, resp)

def set_group_kick(robot: "Concerto", resp: dict):
    url = "/set_group_kick"
    return post(robot, url, resp)

def set_model_show(robot: "Concerto", resp: dict):
    url = "/_set_model_show"
    return post(robot, url, resp)

def get_version_info(robot: "Concerto"):
    result = get(robot, "/get_version_info")
    if result.get("status") == "ok":
        return {
            "app_name": result["data"]["app_name"],
            "app_version": result["data"]["app_version"],
            "protocol_version": result["data"]["protocol_version"],
        }
    else:
        return ""

def group_poke(robot: "Concerto", resp: dict):
    """群聊戳一戳"""
    group_id = resp["group_id"]
    user_id = resp["user_id"]
    url = f"/group_poke?group_id={group_id}&user_id={user_id}"
    return get(robot, url)

def friend_poke(robot: "Concerto", resp: dict):
    """私聊戳一戳"""
    user_id = resp["user_id"]
    url = f"/friend_poke?user_id={user_id}"
    return get(robot, url)

def get_friend_msg_history(robot: "Concerto", resp: dict):
    """获取私聊历史记录"""
    url = "/get_friend_msg_history"
    return post(robot, url, resp)

def get_recent_contact(robot: "Concerto", resp: dict):
    """获取最近消息列表"""
    url = "/get_recent_contact"
    return post(robot, url, resp)

def get_login_info(robot: "Concerto"):
    """获取登录号信息"""
    url = "/get_login_info"
    return get(robot, url)

def set_msg_emoji_like(robot: "Concerto", resp: dict):
    """贴表情"""
    url = "/set_msg_emoji_like"
    return post(robot, url, resp)

def set_group_sign(robot: "Concerto", resp: dict):
    """群签到"""
    url = "/set_group_sign"
    return post(robot, url, resp)

def send_like(robot: "Concerto", resp: dict):
    """群签到"""
    url = "/send_like"
    return post(robot, url, resp)

def set_group_special_title(robot: "Concerto", resp: dict):
    """设置群成员专属头衔"""
    url = "/set_group_special_title"
    return post(robot, url, resp)

def get_group_member_info(robot: "Concerto", resp: dict):
    """获取群成员信息"""
    url = "/get_group_member_info"
    return post(robot, url, resp)

def bot_exit(robot: "Concerto"):
    """退出机器人"""
    url = "/bot_exit"
    return get(robot, url)
