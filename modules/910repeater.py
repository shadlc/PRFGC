"""复读机模块"""

import random
import re

from colorama import Fore
from src.utils import Module, via


class Repeater(Module):
    """复读机模块"""

    ID = "Repeater"
    NAME = "复读机模块"
    HELP = {
        2: [
            "顾名思义，会以一定概率复读重复说过的话，短时间不会重复复读",
        ],
        1: [
            "[开启|关闭]复读机 | 打开或关闭复读机",
            "禁止复读[关键词] | 不再对指定关键词进行复读",
        ],
    }
    CONFIG = "repeater.json"
    GLOBAL_CONFIG = {}
    CONV_CONFIG = {
        "repeat": True,
        "exclude": [],
    }

    @via(lambda self: not self.at_or_private() and self.au(2)
        and self.config[self.owner_id]["repeat"]
        and self.event.msg not in self.config[self.owner_id].get("exclude")
        and re.sub(r",url=.*?]","]", str(self.data.past_message)).count(f"'message': '{self.event.msg}") > 1, success=False)
    def repeat(self):
        """复读机"""
        self.printf(f"在群{Fore.MAGENTA}{self.event.group_name}({self.event.group_id}){Fore.RESET}检测到来自"
                    f"{Fore.MAGENTA}{self.event.user_name}({self.event.user_id}){Fore.RESET}的多次复读：{self.event.msg}")
        if str(self.data.past_message).count("#Already_Repeat"):
            self.printf("该群短时间内已复读过，不再进行复读")
        elif self.match(r"请使用QQ最新版本"):
            self.printf("该消息包含无法读取消息，不进行复读")
        else:
            def get_chance(repeat_count=2):
                p0 = 0.4 # 初始概率
                return 1 - (1 - p0) * (0.5 ** (repeat_count - 2))

            repeat_count = re.sub(r",url=.*?]","]", str(self.data.past_message)).count(f"'message': '{self.event.msg}")
            chance = get_chance(repeat_count)
            if random.random() < chance:
                self.data.past_message[-1]["message"] += "#Already_Repeat"
                msg = self.event.msg
                self.reply(msg)
                self.printf(f"本次概率{f"{round(chance*100,2)}%"}, 复读成功")
            else:
                self.printf(f"本次概率{f"{round(chance*100,2)}%"}, 复读失败")

    @via(lambda self: self.group_at() and self.au(1) and self.match(r"^(开启|打开|启用|允许|关闭|禁止|不允许|取消)?复读机$"))
    def setting(self):
        """设置复读机"""
        flag = self.config[self.owner_id]["repeat"]
        text = "开启" if self.config[self.owner_id]["repeat"] else "关闭"
        if self.match(r"(开启|打开|启用|允许)"):
            flag = True
            text = "开启"
        elif self.match(r"(关闭|禁止|不允许|取消)"):
            flag = False
            text = "关闭"
        msg = f"复读机功能已{text}"
        self.config[self.owner_id]["repeat"] = flag
        self.save_config()
        self.reply(msg)

    @via(lambda self: self.group_at() and self.au(2) and self.match(r"^(不复读|禁止复读)\s+(\S+)$"))
    def exclude(self):
        """复读排除"""
        text = self.match(r"^不复读\s+(\S+)$").groups()[0]
        if not self.config[self.owner_id].get("exclude"):
            self.config[self.owner_id]["exclude"] = []
        self.config[self.owner_id]["exclude"].append(text)
        self.save_config()
        msg = f"成功将[{text}]添加到复读屏蔽词中!"
        self.reply(msg)
        self.printf(f"会话[{self.owner_id}]{msg}")
