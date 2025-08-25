"""抽老婆模块"""
import random
import datetime
import re
from src.utils import Module, build_node, send_forward_msg, via, get_user_name

class Drawife(Module):
    """抽老婆模块"""
    ID = "Drawife"
    NAME = "抽老婆模块"
    HELP = {
        0: [
            "抽老婆模块，无需使用@，直接发送关键词即可",
        ],
        2: [
            "抽老婆 | 看看今天的二次元老婆是谁",
            "添加老婆+人物名称+图片 | 添加老婆",
            "查老婆@某人 | 查询别人老婆",
        ],
    }
    CONFIG = "drawife.json"
    GLOBAL_CONFIG = {
        "pic_path": "drawife",
    }
    CONV_CONFIG = {
        "enable": False,
        "auth_add": 1,
        "wife_history": {}
    }

    @via(lambda self: self.au(2) and self.match(r"^抽老婆$"))
    def draw_wife(self):
        pass