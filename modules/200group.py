"""群组处理模块"""

from src.utils import Module, group_member_info, group_special_title, status_ok, via


class Group(Module):
    """群组处理模块"""

    ID = "Group"
    NAME = "群组处理模块"
    HELP = {
        1: [
            "为[QQ账号或昵称](设置)头衔[头衔] | 为用户设置专属头衔",
        ],
    }
    CONFIG = "group.json"
    GLOBAL_CONFIG = None
    CONV_CONFIG = None

    @via(lambda self: self.group_at() and self.au(1)
        and self.match(r"^(为|给|替)\s*(\S+)\s*(设置|添加|增加|颁发|设立)(专属)*(头衔|称号)\s*(\S+)$"))
    def special_title(self):
        member_info = group_member_info(
            self.robot, self.event.group_id, self.event.self_id
        )
        if member_info.get("role") != "owner":
            self.reply("设置失败，仅群主可以为成员设置专属头衔")
            return
        inputs = self.match(
            r"^(为|给|替)\s*(\S+)\s*(设置|添加|增加|颁发|设立)(专属)*(头衔|称号)\s*(\S+)$"
        ).groups()
        user_id = inputs[1]
        title = inputs[4]
        if user_id == "我":
            user_id = self.event.user_id
        info = group_special_title(self.robot, self.event.group_id, user_id, title)
        if status_ok(info):
            self.reply(f"为{user_id}设置群头衔[{title}]成功!")
        else:
            self.reply(f"为{user_id}设置群头衔[{title}]失败!")
