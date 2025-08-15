"""机器人基础消息处理模块"""

import time

from colorama import Fore
import requests
from src.api import del_msg, get_version_info, send_msg
from src.utils import Module, get_group_name, get_user_name, status_ok, via, build_node, send_forward_msg


class Message(Module):
    """基础消息处理模块"""
    ID = "Message"
    NAME = "基础消息处理模块"
    HELP = {
        1: [
            "[对接|删除]本群 | 对接或删除本群",
            "[增加|删除]管理员 | 修改管理员",
            "撤回 | 撤回机器人上一条消息",
            "重启 | 重启机器人",
            "信息 | 获取机器人基础信息",
            "调试 | 开关调试模式",
            "静默 | 开关静默模式",
        ],
        2: [
            "测试 | 进行基准测试",
            "语音 [文字] | 文字转语音",
            "向(群)说[文字] | 操控机器人发消息",
        ], 
        3: [
            "权限 | 查看权限等级",
            "计时 [数字] | 进行异步计时",
        ]
    }
    CONFIG = "data.json"
    GLOBAL_CONFIG = {
        "ip_test_token": ""
    }
    CONV_CONFIG = {
        "recall": False
    }

    @via(lambda self: self.at_or_private() and self.au(3) and self.match(r"^帮助$"))
    def help(self):
        help_list = []
        for mod in self.robot.modules.values():
            if mod.NAME is None or not isinstance(mod.HELP, dict):
                continue
            help_text = ""
            for i in range(4):
                if self.au(i):
                    for text in mod.HELP.get(i, []):
                        help_text += f"{text}\n"
            if help_text:
                help_text = f"{mod.NAME}帮助\n\n{help_text}"
                help_list.append(build_node(help_text.strip(), nickname=self.robot.self_name))
        nodes = [
            build_node("ConcertBot HELP", nickname=self.robot.self_name),
            *help_list
        ]
        if self.event.group_id:
            send_forward_msg(self.robot, nodes, group_id=self.event.group_id)
        else:
            send_forward_msg(self.robot, nodes, user_id=self.event.user_id)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^(增加|添加|删除|取消)?\s?管理员"))
    def admin(self):
        if self.match(r"^(增加|添加)\s?管理员\s?[0-9]+"):
            user_id = self.match(r"^(增加|添加)\s?管理员\s?([0-9]+)").groups()[1]
            user_name = get_user_name(self.robot, user_id)
            if user_id not in self.robot.config.admin_list:
                self.robot.config.admin_list.append(user_id)
                self.robot.config.save("admin_list", self.robot.config.admin_list)
                msg = f"{user_name}({user_id})已设置为管理员"
                self.printf(msg)
            else:
                msg = f"{user_name}({user_id})已经是管理员！"
                self.warnf(msg)

        elif self.match(r"^(删除|取消)\s?管理员\s?[0-9]+"):
            user_id = self.match(r"^(删除|取消)管理员\s?([0-9]+)").groups()[1]
            user_name = get_user_name(self.robot, user_id)
            if user_id in self.robot.config.admin_list:
                self.robot.config.admin_list.remove(user_id)
                self.robot.config.save("admin_list", self.robot.config.admin_list)
                msg = f"{user_name}({user_id})不再是管理员"
                self.printf(msg)
            else:
                msg = f"{user_name}({user_id})不是管理员！"
                self.warnf(msg)
        else:
            msg = "请使用 [增加|删除]管理员 [QQ号] 进行增添管理员"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.match(r"^权限(等级)?$"))
    def authority(self):
        if self.au(0):
            auth_level = "后台权限"
        elif self.au(1):
            auth_level = "管理员权限"
        elif self.au(2):
            auth_level = "全功能权限"
        elif self.au(3):
            auth_level = "普通权限"
        else:
            auth_level = "未知权限"
        msg = f"您的权限等级为: {auth_level}"
        self.reply(msg)

    @via(lambda self: self.group_at() and self.au(1)
         and self.match(r"^(对接|监听|添加|增加|记录|删除|取消|移除)(本群|此群|该群|这个群|这群|群)?$"))
    def connect(self):
        group_id = str(self.event.group_id)
        group_name = get_group_name(self.robot, group_id)
        msg = ""
        if self.match(r"(对接|监听|添加|增加|记录)"):
            if group_id not in self.robot.config.rev_group:
                self.robot.config.rev_group.append(group_id)
                self.robot.config.save("rev_group", self.robot.config.rev_group)
                self.printf(f"群{Fore.MAGENTA}{group_name}({group_id}){Fore.RESET}已添加至对接群列表")
                msg = "已成功对接本群！"
            else:
                msg = "本群已经在对接群列表中！"
        elif self.match(r"(删除|取消|移除)"):
            if group_id in self.robot.config.rev_group:
                self.robot.config.rev_group.remove(group_id)
                self.robot.config.save("rev_group", self.robot.config.rev_group)
                msg = "已成功从对接群列表移除本群！"
                self.printf(
                    f"群{Fore.MAGENTA}{group_name}({group_id}){Fore.RESET}已从对接群列表中移除"
                )
            else:
                msg = "本群不在对接列表！"
        self.reply(msg, True)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^(开启|关闭)?调试(模式)?$"))
    def debug(self):
        if self.match(r"^开启"):
            self.robot.config.is_debug = True
        elif self.match(r"^关闭"):
            self.robot.config.is_debug = False
        else:
            self.robot.config.is_debug = not self.robot.config.is_debug
        self.robot.config.save("is_debug", self.robot.config.is_debug)
        if self.robot.config.is_debug:
            msg = "调试模式已开启"
            self.warnf("调试模式已开启")
        else:
            msg = "调试模式已关闭"
            self.warnf("调试模式已关闭")
        self.reply(msg, True)

    @via(lambda self: self.at_or_private() and self.match(r"^计时[0-9]+"))
    def delay(self):
        sleep_time = int(self.match(r"([0-9]+)").groups()[0])
        msg = f"计时{sleep_time}秒开始"
        self.reply(msg)
        time.sleep(sleep_time)
        msg = f"计时{sleep_time}秒结束"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^信息$"))
    def info(self):
        info = get_version_info(self.robot)
        msg = "=======API版本信息======="
        msg += f"\n应用名：{info["app_name"]}"
        msg += f"\n版本号：{info["app_version"]}"
        msg += f"\n协议版本：{info["protocol_version"]}"
        msg += "\n==========内部信息=========="
        msg += f"\n调试模式: {self.robot.config.is_debug}"
        msg += f"\n管理员列表：{self.robot.config.admin_list}"
        msg += f"\n对接群列表：{self.robot.config.rev_group}"
        msg += f"\n已安装模块：{[f"{i.NAME}({i.ID})" for i in self.robot.modules.values()]}"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^(撤回|闭嘴|嘘)(！|，)?(懂？)?$"))
    def recall(self):
        if len(self.robot.self_message):
            rev = self.robot.self_message[-1]
            msg_id = rev["message_id"]
            msg = rev["message"]
            result = del_msg(self.robot, {"message_id": msg_id})
            self.robot.self_message.pop()
            if status_ok(result):
                self.printf(f"撤回消息{Fore.MAGENTA}{msg}{Fore.RESET}成功！")
            else:
                msg = f"撤回消息{Fore.MAGENTA}{msg}{Fore.RESET}失败！"
                self.reply(msg)
        else:
            msg = "暂无可撤回的历史消息"
            self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^重启$"))
    def restart(self):
        self.reply("%REBOOTING%")
        self.robot.is_running = False
        self.robot.is_restart = True

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^向?群?([0-9]+)?说\s?\S+$"))
    def say(self):
        if self.match(r"^向"):
            inputs = self.match(r"([0-9]+)说\s?(\S*)").groups()
            number = inputs[0]
            send = inputs[1]
            result = False
            if self.match(r"向群[0-9]+"):
                result = status_ok(
                    send_msg(self.robot, {"msg_type": "group", "number": number, "msg": send})
                )
            else:
                result = status_ok(
                    send_msg(self.robot, {"msg_type": "private", "number": number, "msg": send})
                )
            if result:
                msg = f"发送消息{send}成功！"
            else:
                msg = "发送消息"
        else:
            msg = self.match(r"说\s?(\S*)").groups()[0]
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^(开启|关闭)?防撤回$"))
    def recall_setting(self):
        flag = self.config[self.owner_id].get("recall", False)
        text = "开启" if flag else "关闭"
        if self.match(r"(开启|打开|启用|允许)"):
            flag = True
            text = "开启"
        elif self.match(r"(关闭|禁止|不允许|取消)"):
            flag = False
            text = "关闭"
        msg = f"群防撤回已{text}"
        self.config[self.owner_id]["recall"] = flag
        self.save_config(self.config[self.owner_id], self.owner_id)
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^(开启|关闭)?静默(模式)?$"))
    def silence(self):
        if self.match(r"^开启"):
            self.robot.is_silence = True
        elif self.match(r"^关闭"):
            self.robot.is_silence = False
        else:
            self.robot.is_silence = not self.robot.is_silence
        self.robot.config.save("is_silence", self.robot.config.is_silence)
        if self.robot.is_silence:
            msg = "静默模式已开启"
        else:
            msg = "静默模式已关闭"
        self.warnf(msg)
        self.reply(msg, True)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^测试"))
    def test(self):
        if self.match(r"^测试错误"):
            raise RuntimeError("测试错误")
        elif self.match(r"^测试ip\s(\S*)"):
            ip = self.match(r"^测试ip\s(\S*)").groups()[0]
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "token": self.config.get("ip_test_token",""),
            }
            url = f"https://api.ip138.com/ip/?ip={ip}"
            msg = ""
            try:
                data = requests.post(url, headers=headers, timeout=5).json()
                if data.get("ret") != "ok":
                    msg = f"ip138.com返回为空: {data.get("msg")}"
                else:
                    ip = data.get("ip")
                    location = data.get("data")
                    msg = f"IP地址: {ip}\n地区: {" ".join([i for i in location[:-4]])}\n归属: {location[-3]}\n邮编: {location[-2]}\n区号: {location[-1]}"
            except requests.exceptions.JSONDecodeError as e:
                msg = f"返回解析错误！{e}"
            except requests.ConnectionError as e:
                msg = f"ip138.com服务器请求错误！{e}"
        else:
            thing = self.match(r"^测试(.*)").groups()[0]
            msg = f"测试{thing}OK!"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^语音\s?\S*"))
    def voice(self):
        if self.match(r"语音\s?\S+"):
            msg = (
                "[CQ:tts,text="
                + self.match(r"语音\s?(\S+)").groups()[0]
                + " ]"
            )
        else:
            msg = "[CQ:tts,text=请输入需要让我读出来的字嘛]"
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(1) and self.match(r"^(在吗|你好)$"))
    def reply_msg(self):
        if "在吗" == self.event.msg:
            self.reply("%ROBOT_NAME%正在工作呢~\nBig brother is watching you!")
        elif "你好" == self.event.msg:
            self.reply("你好！我是%ROBOT_NAME%,请@我并发送“帮助”来让我帮助您~")
        else:
            self.go_on()

