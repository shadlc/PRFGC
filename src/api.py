"""API定义"""

import json
import time

from typing import TYPE_CHECKING

import requests
from colorama import Fore

if TYPE_CHECKING:
    from robot import Concerto

def status_ok(response):
    if response.get("status") == "ok":
        return True
    else:
        return False

def get(robot: "Concerto", url):
    try:
        get_url = robot.config.api_base + url
        robot.request_list.append(f"GET{url}")
        r = requests.get(get_url, timeout=5)
        rev_json = r.json()
        if robot.config.is_debug:
            robot.printf(f"{Fore.YELLOW}[DATA]{Fore.RESET} GET请求{Fore.MAGENTA}[{get_url}]{Fore.RESET}后返回{Fore.YELLOW}{r.json()}{Fore.RESET}")
        return rev_json
    except json.JSONDecodeError:
        robot.errorf("数据解析错误！")
        return {}
    except requests.exceptions.InvalidURL:
        robot.errorf("无效的请求地址！")
        return {}
    except Exception as e:
        raise e

def post(robot: "Concerto", url, data):
    try:
        data = json.dumps(data, ensure_ascii=False)
        get_url = robot.config.api_base + url
        robot.request_list.append(f"POST{url} | {data}")
        header = {"Content-Type": "application/json"}
        r = requests.post(get_url, headers=header, data=data.encode("utf-8"), timeout=5)
        rev_json = r.json()
        if robot.config.is_debug:
            robot.printf(f"{Fore.YELLOW}[DATA]{Fore.RESET} POST请求{Fore.MAGENTA}[{get_url}]{Fore.RESET}后返回{Fore.YELLOW}{r.json()}{Fore.RESET}")
        return rev_json
    except json.JSONDecodeError:
        robot.errorf("数据解析错误！")
        return {}
    except requests.exceptions.InvalidURL:
        robot.errorf("无效的请求地址！")
        return {}
    except Exception as e:
        raise e

def connect_api(robot: "Concerto"):
    connected = False
    while not connected:
        print(".", end="", flush=True)
        try:
            result = get(robot, "/get_version_info")
        except requests.exceptions.ConnectionError:
            continue
        connected = True if status_ok(result) else False
        app_name = result.get("data",{}).get("app_name")
        app_version = result.get("data",{}).get("app_version")
        time.sleep(1)
    robot.printf(f"已连接至 {Fore.YELLOW}{app_name}v{app_version}{Fore.RESET}", flush=True)
    robot.api_name = f"{app_name}v{app_version}"
    result = get(robot, "/get_login_info")
    robot.self_name = result["data"]["nickname"]
    robot.self_id = str(result["data"]["user_id"])
    robot.at_info = "[CQ:at,qq=" + str(robot.self_id) + "]"
    return [result["data"]["nickname"], result["data"]["user_id"]]

def send_msg(robot: "Concerto", resp_dict):
    msg_type = resp_dict.get("msg_type")  # 回复类型（群聊/私聊）
    number = resp_dict.get("number")  # 回复账号（群号/好友号）
    group_id = resp_dict.get("group_id")  # 临时会话群号（群号）
    msg = str(resp_dict.get("msg"))  # 要回复的消息
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

def del_msg(robot: "Concerto", resp_dict):
    message_id = resp_dict["message_id"]  # 消息ID
    url = "/delete_msg?message_id=" + str(message_id)
    return get(robot, url)

def get_msg(robot: "Concerto", resp_dict):
    message_id = resp_dict["message_id"]  # 消息ID
    url = "/get_msg?message_id=" + str(message_id)
    return get(robot, url)

def get_forward_msg(robot: "Concerto", resp_dict):
    return post(robot, "/get_forward_msg", resp_dict)

def send_group_notice(robot: "Concerto", resp_dict):
    group_id = resp_dict["group_id"]  # 群号
    content = resp_dict["content"]  # 公告内容
    url = "/_send_group_notice?group_id=" + str(group_id) + "&content=" + content
    return get(robot, url)

def get_image(robot: "Concerto", resp_dict):
    file = resp_dict["file"]  # 图片缓存文件名
    url = "/get_image?file=" + str(file)
    return get(robot, url)

def handle_quick_operation(robot: "Concerto", resp_dict):
    context = resp_dict["context"]  # 事件数据对象
    operation = resp_dict["operation"]  # 快速操作对象
    url = "/.handle_quick_operation"
    operation = {"context": context, "operation": operation}
    return post(robot, url, operation)

def ocr_image(robot: "Concerto", resp_dict):
    image = resp_dict["image"]  # 图片ID
    url = "/.ocr_image?image=" + image
    return get(robot, url)

def upload_private_file(robot: "Concerto", resp_dict):
    user_id = resp_dict["user_id"]  # 用户ID
    file = resp_dict["file"]  # 本地目录
    name = resp_dict["name"]  # 文件名称
    url = (
        "/upload_private_file?group_id="
        + str(user_id)
        + "&file="
        + file
        + "&name="
        + name
    )
    return get(robot, url)

def upload_group_file(robot: "Concerto", resp_dict):
    group_id = resp_dict["group_id"]  # 群号
    file = resp_dict["file"]  # 本地目录
    name = resp_dict["name"]  # 文件名称
    url = (
        "/upload_group_file?group_id="
        + str(group_id)
        + "&file="
        + file
        + "&name="
        + name
    )
    return get(robot, url)

def get_group_msg_history(robot: "Concerto", resp_dict):
    group_id = resp_dict["group_id"]  # 群号
    if "message_seq" in resp_dict:
        message_seq = resp_dict["message_seq"]
        url = (
            "/get_group_msg_history?group_id="
            + str(group_id)
            + "&message_seq="
            + str(message_seq)
        )
    else:
        url = "/get_group_msg_history?group_id=" + str(group_id)
    return get(robot, url)["data"]["messages"]

def get_stranger_info(robot: "Concerto", resp_dict):
    user_id = resp_dict["user_id"]  # 目标QQ号
    url = "/get_stranger_info?user_id=" + str(user_id)
    return get(robot, url)

def get_group_info(robot: "Concerto", resp_dict):
    group_id = resp_dict["group_id"]  # 目标群号
    url = "/get_group_info?group_id=" + str(group_id)
    return get(robot, url)

def get_model_show(robot: "Concerto", resp_dict):
    model = resp_dict["model"]  # 机型
    url = "/_set_model_show?model=" + model
    return get(robot, url)

def set_model_show(robot: "Concerto", resp_dict):
    model = resp_dict["model"]  # 机型
    model_show = resp_dict["model_show"]  # 机型后缀
    url = "/_set_model_show?model=" + model + "&model_show=" + model_show
    return get(robot, url)

def get_version_info(robot: "Concerto"):
    result = get(robot, "/get_version_info")
    if status_ok(result):
        return {
            "app_name": result["data"]["app_name"],
            "app_version": result["data"]["app_version"],
            "protocol_version": result["data"]["protocol_version"],
        }
    else:
        return ""

def group_poke(robot: "Concerto", resp_dict):
    """群聊戳一戳"""
    group_id = resp_dict["group_id"]
    user_id = resp_dict["user_id"]
    url = f"/group_poke?group_id={group_id}&user_id={user_id}"
    return get(robot, url)

def friend_poke(robot: "Concerto", resp_dict):
    """私聊戳一戳"""
    user_id = resp_dict["user_id"]
    url = f"/friend_poke?user_id={user_id}"
    return get(robot, url)

def get_friend_msg_history(robot: "Concerto", resp_dict):
    """获取私聊历史记录"""
    url = "/get_friend_msg_history"
    return post(robot, url, resp_dict)

def get_recent_contact(robot: "Concerto", resp_dict):
    """获取最近消息列表"""
    url = "/get_recent_contact"
    return post(robot, url, resp_dict)

def get_login_info(robot: "Concerto"):
    """获取登录号信息"""
    url = "/get_login_info"
    return get(robot, url)

def set_msg_emoji_like(robot: "Concerto", resp_dict):
    """贴表情"""
    url = "/set_msg_emoji_like"
    return post(robot, url, resp_dict)

def set_group_sign(robot: "Concerto", resp_dict):
    """群签到"""
    url = "/set_group_sign"
    return post(robot, url, resp_dict)

def send_like(robot: "Concerto", resp_dict):
    """群签到"""
    url = "/send_like"
    return post(robot, url, resp_dict)

def set_group_special_title(robot: "Concerto", resp_dict):
    """设置群成员专属头衔"""
    url = "/set_group_special_title"
    return post(robot, url, resp_dict)

def get_group_member_info(robot: "Concerto", resp_dict):
    """获取群成员信息"""
    url = "/get_group_member_info"
    return post(robot, url, resp_dict)

def bot_exit(robot: "Concerto"):
    """退出机器人"""
    url = "/bot_exit"
    return get(robot, url)
