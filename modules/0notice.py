"""机器人基础通知处理模块"""

import random
import time

from colorama import Fore

from src.utils import Module, calc_size, poke, reply_id, via


class Notice(Module):
    """基础通知处理模块"""

    ID = "Notice"
    NAME = "基础通知处理模块"
    HELP = None
    CONFIG = "data.json"
    GLOBAL_CONFIG = None
    CONV_CONFIG = {
        "recall": False
    }

    @via(lambda self: self.event.notice_type == "notify"
        and self.event.sub_type == "poke"
        and not self.is_self_send())
    def poke(self):
        if self.event.group_id:
            self.printf(
                f"在群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}接收来自"
                f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}的戳一戳"
            )
            if random.choice(range(5)) == 0:
                self.printf(
                    f"20%概率触发，尝试对{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}进行反戳"
                )
                poke(self.robot, self.event.user_id, self.event.group_id)
                if self.event.target_id == self.robot.self_id:
                    reply_id(self.robot, "group", self.event.group_id, "%BE_POKED%")
        else:
            self.printf(
                f"{Fore.YELLOW}[{self.ID}] 接收来自"
                f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}的戳一戳"
            )
            self.printf(
                f"尝试对{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}进行反戳"
            )
            poke(self.robot, self.event.user_id)

    @via(lambda self: self.event.notice_type == "notify"
        and self.event.sub_type == "input_status"
        and self.event.raw.get("status_text"))
    def typing(self):
        if status_text := self.event.raw.get("status_text"):
            self.printf(f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}{status_text}")

    @via(lambda self: self.event.notice_type == "client_status")
    def client_status(self):
        if self.event.raw["online"]:
            self.printf(
                f"检测到本账号在客户端{Fore.MAGENTA}{self.event.raw["client"]["device_name"]}{Fore.RESET}登录"
            )
        else:
            self.printf(
                f"检测到本账号在客户端{Fore.MAGENTA}{self.event.raw["client"]["device_name"]}{Fore.RESET}登出"
            )

    @via(lambda self: self.event.notice_type == "friend_add")
    def friend_add(self):
        self.printf(
            f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}已加为好友"
        )

    @via(lambda self: self.event.notice_type == "friend_recall")
    def friend_recall(self):
        self.printf(
            f"{Fore.MAGENTA}{self.event.operator_name}({self.event.operator_id})撤回了一条消息"
        )
        msg = "%OTHER_RECALL%"
        reply_id(self.robot, "private", self.event.user_id, msg)

    @via(lambda self: self.event.notice_type == "group_recall")
    def group_recall(self):
        self.printf(
            f"在群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}检测到一条撤回消息"
        )
        recall_time = time.strftime(
            "%Y年%m月%d日%H:%M:%S", time.localtime(self.event.time)
        )
        recall_message = None
        if (
            self.event.user_id == self.robot.self_id
            and self.event.operator_id != self.robot.self_id
            and self.event.operator_id not in self.robot.admin_id
        ):
            msg = f"{self.event.operator_name}在{recall_time}将%ROBOT_NAME%的消息撤回，%ROBOT_NAME%很难过"
            reply_id(self.robot, "group", self.event.group_id, msg)
        elif self.event.user_id != self.robot.self_id:
            if self.config[self.owner_id].get("recall"):
                for message in self.data.past_message:
                    if (
                        "message_id" in message
                        and self.event.msg_id == message["message_id"]
                    ):
                        recall_message = message["raw_message"]
                if recall_message is not None:
                    msg = f"%OTHER_RECALL%\n{self.event.operator_name}在{recall_time}试图将{self.event.user_name}的一条消息“{recall_message}”撤回，%ROBOT_NAME%还记得"
                else:
                    msg = f"{self.event.operator_name}在{recall_time}将{self.event.user_name}的一条消息撤回，但是%ROBOT_NAME%记不得了..."
                reply_id(self.robot, "group", self.event.group_id, msg)
        print(self.NAME, "else")

    @via(lambda self: self.event.notice_type == "group_upload")
    def group_upload(self):
        file_name = self.event.raw["file"]["name"]
        file_size = calc_size(self.event.raw["file"]["size"])
        self.printf(
            f"群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}内{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}上传了文件{Fore.YELLOW}{file_name}({file_size})"
        )

    @via(lambda self: self.event.notice_type == "group_admin")
    def group_admin(self):
        if self.event.sub_type == "set":
            self.printf(
                f"群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}内{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}被设为管理员"
            )
        elif self.event.sub_type == "unset":
            self.printf(
                f"群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}内管理员{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}被取缔"
            )

    @via(lambda self: self.event.notice_type == "group_decrease")
    def group_decrease(self):
        if self.event.sub_type == "leave":
            self.printf(
                f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}主动退群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}"
            )
        elif self.event.sub_type == "kick":
            self.printf(
                f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}被踢出群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}"
            )

    @via(lambda self: self.event.notice_type == "group_increase")
    def group_increase(self):
        if self.event.sub_type == "approve":
            self.printf(
                f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}已被同意加入群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}"
            )
        elif self.event.sub_type == "invite":
            self.printf(
                f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}已被邀请加入群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}"
            )

        self.printf(str(self.event.user_id) + "|" + str(self.robot.self_id))
        if self.event.user_id == self.robot.self_id:
            msg = "%SELF_INTRODUCTION%"
            reply_id(self.robot, "group", self.event.group_id, msg)
        else:
            msg = self.event.user_name + "%WELCOME_NEWBIE%"
            reply_id(self.robot, "group", self.event.group_id, msg)

    @via(lambda self: self.event.notice_type == "group_ban")
    def group_ban(self):
        duration = self.event.raw["duration"]
        if duration:
            duration = str(duration) + "秒" if int(duration) < 268435455 else "永久"
        if self.event.user_id == 0:
            if self.event.sub_type == "ban":
                self.printf(
                    f"{Fore.YELLOW}[{self.ID}]{Fore.RESET}群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}内{Fore.MAGENTA}{self.event.operator_name}({self.event.operator_id}){Fore.RESET}设置了{Fore.YELLOW}{duration}{Fore.RESET}的全员禁言"
                )
            elif self.event.sub_type == "lift_ban":
                self.printf(
                    f"{Fore.YELLOW}[{self.ID}]{Fore.RESET}群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}内{Fore.MAGENTA}{self.event.operator_name}({self.event.operator_id}){Fore.RESET}解除了全员禁言"
                )
        else:
            if self.event.sub_type == "ban":
                self.printf(
                    f"{Fore.YELLOW}[{self.ID}]{Fore.RESET}群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}内{Fore.MAGENTA}{self.event.operator_name}({self.event.operator_id}){Fore.RESET}为{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}设置了{Fore.YELLOW}{duration}{Fore.RESET}的禁言"
                )
            elif self.event.sub_type == "lift_ban":
                self.printf(
                    f"{Fore.YELLOW}[{self.ID}]{Fore.RESET}群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}内{Fore.MAGENTA}{self.event.operator_name}({self.event.operator_id}){Fore.RESET}解除了{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}的禁言"
                )

    @via(lambda self: self.event.notice_type == "notify" and self.event.sub_type == "profile_like")
    def profile_like(self):
        times = self.event.raw.get("times")
        self.printf(
            f"{Fore.MAGENTA}{self.event.operator_id}({self.event.operator_nick}){Fore.RESET}给你的主页点了{Fore.YELLOW}{times}{Fore.RESET}个赞"
        )
