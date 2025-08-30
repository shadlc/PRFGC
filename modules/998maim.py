"""麦麦适配器模块"""

import asyncio
import base64
import json
import html
import io
import logging
import re
import threading
import time
import traceback
from typing import Any, Dict, List

from colorama import Fore
from PIL import Image
import httpx

from maim_message import (
    BaseMessageInfo,
    FormatInfo,
    UserInfo,
    GroupInfo,
    MessageBase,
    Seg,
    Router,
    RouteConfig,
    TargetConfig,
)

from src.utils import (
    Module,
    apply_formatter,
    del_msg,
    get_forward_msg,
    get_msg,
    group_member_info,
    poke,
    reply_id,
    send_group_ai_record,
    set_group_ban,
    set_group_kick,
    set_group_whole_ban,
    status_ok,
    via,
)

class Maim(Module):
    """麦麦适配器模块"""

    ID = "Maim"
    NAME = "麦麦适配器模块"
    HELP = {
        0: [
            "本模块用于对接麦麦机器人，感谢[MaiBot][MaiBot-Napcat-Adapter]对本模块的实现提供助力"
        ],
        1: [
            "[开启|关闭]麦麦 | 开启或关闭麦麦机器人功能",
        ],
    }
    CONFIG = "maimbot.json"
    GLOBAL_CONFIG = {
        "platform": "qq",
        "url": "",
    }
    CONV_CONFIG = {
        "enable": True,
        "blacklist": [],
    }
    AUTO_INIT = True

    def __init__(self, event, auth=0):
        super().__init__(event, auth)
        if self.ID in self.robot.persist_mods:
            return
        self.robot.persist_mods[self.ID] = self
        if not self.config["url"]:
            self.errorf("未配置MaiMBot链接地址，模块已禁用")
            return
        logger = logging.getLogger('maim_message')
        logger.setLevel(logging.INFO)
        apply_formatter(logger, self.ID)
        self.loop = asyncio.get_event_loop()
        target_config = TargetConfig(url=self.config["url"], token=None)
        route_config = RouteConfig({self.config["platform"]: target_config})
        self.router = Router(route_config)
        self.router.register_class_handler(self.handle_maimbot_message)
        self.router_run()

    def premise(self):
        if self.ID in self.robot.persist_mods:
            maim: Maim = self.robot.persist_mods[self.ID]
            self.router = maim.router
            self.loop = maim.loop
        return self.config["url"]

    def router_run(self, router=None):
        """启动"""
        if router is None:
            router = self.router
        threading.Thread(target=self.listening, args=(router,), daemon=True, name=self.NAME).start()

    def listening(self, router=None):
        """开启监听"""
        if router is None:
            router = self.router
        while True:
            self.loop.run_until_complete(router.run())

    async def handle_maimbot_message(self, raw_message: dict):
        """处理 MaiMBot 回复的消息"""
        try:
            message: MessageBase = MessageBase.from_dict(raw_message)
            simple_msg = ""
            if self.robot.config.is_debug:
                simple_msg = str(raw_message)
            else:
                simple_msg = str(message.message_segment)
            simple_msg = re.sub(
                r"type='(image|emoji)',\s?data='.*?'",
                r"type='\1', data='Base64File'",
                simple_msg
            )
            self.printf(f"{Fore.CYAN}[FROM] {Fore.RESET}{simple_msg}")
            message_segment: Seg = message.message_segment
            if message_segment.type == "command":
                return await self.send_command(message)
            else:
                return await self.send_message(message)
        except Exception:
            self.errorf(f"处理来自MaiMBot的消息失败!\n{traceback.format_exc()}")

    async def send_command(self, message_base: MessageBase) -> None:
        """处理命令类"""
        message_info: BaseMessageInfo = message_base.message_info
        segment: Seg = message_base.message_segment
        group_info: GroupInfo = message_info.group_info
        seg_data: Dict[str, Any] = segment.data
        args = seg_data.get("args")
        command: str = seg_data.get("name")
        info = None
        try:
            match command:
                case "set_group_ban":
                    info = set_group_ban(
                        self.robot,
                        group_info.group_id,
                        args.get("user_id"),
                        args.get("duration"),
                    )
                case "set_group_whole_ban":
                    info = set_group_whole_ban(
                        self.robot, group_info.group_id, args.get("enable")
                    )
                case "set_group_kick":
                    info = set_group_kick(
                        self.robot, group_info.group_id, args.get("user_id")
                    )
                case "send_poke":
                    if group_info is None:
                        info = poke(self.robot, args.get("user_id"))
                    else:
                        info = poke(
                            self.robot, args.get("user_id"), group_info.group_id
                        )
                case "delete_msg":
                    info = del_msg(self.robot, args.get("message_id"))
                case "send_group_ai_record":
                    info = send_group_ai_record(
                        self.robot, group_info.group_id, args.get("character"), args.get("text")
                    )
                case _:
                    self.errorf(f"未知命令: {command}")
                    return
        except Exception as e:
            self.errorf(f"处理命令时发生错误: {e}")
            return None

        if status_ok(info):
            self.printf(f"命令 {command} 执行成功")
        else:
            self.warnf(f"命令 {command} 执行失败，napcat返回: {info}")

    async def send_message(self, message_base: MessageBase) -> None:
        """处理消息发送"""
        message_info: BaseMessageInfo = message_base.message_info
        segment: Seg = message_base.message_segment
        group_info: GroupInfo = message_info.group_info
        user_info: UserInfo = message_info.user_info
        target_id: int = None
        msg_type: str = None
        msg: list = []
        try:
            msg = self.handle_seg(segment)
        except Exception as e:
            self.errorf(f"处理MaiMBot消息时发生错误: {e}")
            return

        if not msg:
            self.errorf("暂不支持解析此回复！")
            return None

        if group_info and user_info:
            target_id = group_info.group_id
            msg_type = "group"
        elif user_info:
            target_id = user_info.user_id
            msg_type = "private"
        else:
            self.errorf("无法识别的消息类型")
            return
        info = reply_id(self.robot, msg_type, target_id, msg)
        if status_ok(info):
            qq_message_id = info["data"].get("message_id")
            mmc_message_id = message_base.message_info.message_id
            message_base.message_segment = Seg(
                type="notify",
                data={
                    "sub_type": "echo",
                    "echo": mmc_message_id,
                    "actual_id": qq_message_id,
                },
            )
            await self.send_to_maim(message_base)

    def handle_seg(self, segment: Seg) -> str:
        """处理消息结构"""
        def build_payload(payload: str, msg: str, is_reply: bool = False) -> list:
            """构建发送的消息体"""
            if is_reply:
                temp = ""
                temp += msg
                for i in payload:
                    if i.get("type") == "reply":
                        # 多个回复，使用最新的回复
                        continue
                    temp += i
                return temp
            else:
                payload += msg
                return payload

        def process_message(seg: Seg, payload: str) -> str:
            new_payload = payload
            if seg.type == "reply":
                target_id = seg.data
                if target_id == "notice":
                    return payload
                new_payload = build_payload(payload, f"[CQ:reply,id={target_id}]", True)
            elif seg.type == "text":
                text = seg.data
                if not text:
                    return payload
                new_payload = build_payload(payload, text, False)
            elif seg.type == "face":
                face_id = seg.data
                new_payload = build_payload(payload, f"[CQ:face,id={face_id}]", False)
            elif seg.type == "image":
                image = seg.data
                new_payload = build_payload(payload, f"[CQ:image,file=base64://{image},subtype=0]", False)
            elif seg.type == "emoji":
                emoji = seg.data
                image_format = self.get_image_format(emoji)
                if image_format != "gif":
                    emoji = self.convert_image_to_gif(emoji)
                new_payload = build_payload(payload, f"[CQ:image,file=base64://{emoji},subtype=1,summary=&#91;动画表情&#93;]", False)
            elif seg.type == "voice":
                voice = seg.data
                new_payload = build_payload(payload, f"[CQ:voice,file=base64://{voice}]", False)
            elif seg.type == "voiceurl":
                voice_url = seg.data
                new_payload = build_payload(payload, f"[CQ:record,file={voice_url}]", False)
            elif seg.type == "music":
                song_id = seg.data
                new_payload = build_payload(payload, f"[CQ:music,file={song_id}]", False)
            elif seg.type == "videourl":
                video_url = seg.data
                new_payload = build_payload(payload, f"[CQ:video,file={video_url}]", False)
            elif seg.type == "file":
                file_path = seg.data
                new_payload = build_payload(payload, f"[CQ:file,file=file://{file_path}]", False)
            return new_payload

        payload = ""
        if segment.type == "seglist":
            if not segment.data:
                return []
            for seg in segment.data:
                payload = process_message(seg, payload)
        else:
            payload = process_message(segment, payload)
        return payload

    async def handle_msg(self, raw: str, in_reply: bool = False) -> List[Seg] | None:
        """处理实际消息"""
        msg: str = raw.get("message")
        if not msg:
            return None
        if "CQ:json" in msg:
            msg = re.sub(r"(\s)+", "", msg)
        seg_message: List[Seg] = []
        while re.search(r"(\[CQ:(.+?),(.+?)\])", msg):
            cq_code, cq_type, cq_data = re.search(r"(\[CQ:(.+?),(.+?)\])", msg).groups()
            data = {}
            for item in cq_data.split(","):
                k, v = item.split("=", maxsplit=1)
                if v.isdigit():
                    data[k] = int(v)
                else:
                    data[k] = html.unescape(v)
            seg = None
            match cq_type:
                case "face":
                    face_id = str(data.get("id"))
                    face_content: str = qq_face.get(face_id)
                    seg = Seg(type="text", data=face_content)
                case "reply":
                    if not in_reply:
                        msg_id = data.get("id")
                        detail = get_msg(self.robot, msg_id).get("data", {})
                        reply_msg = await self.handle_msg(detail, in_reply=True)
                        if reply_msg is None:
                            reply_msg = "(获取发言内容失败)"
                        sender_name: str = detail.get("sender", {}).get("nickname")
                        sender_id: str = detail.get("sender", {}).get("user_id")
                        ret_seg: List[Seg] = []
                        if not sender_name:
                            ret_seg.append(Seg(type="text", data="[回复 未知用户："))
                        else:
                            ret_seg.append(Seg(type="text", data=f"[回复<{sender_name}:{sender_id}>："))
                        ret_seg += reply_msg
                        ret_seg.append(Seg(type="text", data="]，说："))
                        seg = ret_seg
                case "record":
                    seg = Seg(type="text", data="<语音>")
                case "video":
                    seg = Seg(type="text", data="<视频>")
                case "at":
                    qq_id = data.get("qq")
                    if str(self.event.self_id) == str(qq_id):
                        seg = Seg(type="text", data=f"@<{self.robot.self_name}:{self.robot.self_id}>")
                    else:
                        info = group_member_info(self.robot, self.event.group_id, qq_id)
                        if info:
                            seg = Seg(type="text", data=f"@<{info["data"].get('nickname')}:{info["data"].get('user_id')}>")
                case "rps":
                    seg = Seg(type="text", data="<猜拳>")
                case "dice":
                    seg = Seg(type="text", data="<骰子>")
                case "shake":
                    seg = Seg(type="poke", data="<戳一戳>")
                case "anonymous":
                    seg = Seg(type="text", data="<匿名聊天>")
                case "share":
                    seg = Seg(type="text", data="<分享>")
                case "contact":
                    seg = Seg(type="text", data="<名片>")
                case "location":
                    seg = Seg(type="text", data="<定位>")
                case "music":
                    seg = Seg(type="text", data="<音乐>")
                case "image":
                    try:
                        url = data.get("url")
                        image_base64 = await self.get_image_base64(url)
                        sub_type = data.get("sub_type")
                        if sub_type == 0:
                            seg = Seg(type="image", data=image_base64)
                        elif sub_type not in [4, 9]:
                            seg = Seg(type="emoji", data=image_base64)
                        else:
                            self.warnf(f"不支持的图片子类型：{sub_type}")
                    except Exception as e:
                        self.errorf(f"图片消息处理失败: {str(e)}")
                case "redbag":
                    seg = Seg(type="text", data="<红包>")
                case "poke":
                    seg = Seg(type="text", data="<戳一戳>")
                case "gift":
                    seg = Seg(type="text", data="<礼物>")
                case "forward":
                    msg_id = str(data.get("id"))
                    info = get_forward_msg(self.robot, msg_id)
                    if status_ok(info):
                        msg_list = info["data"].get("messages")
                        ret_seg: List[Seg] = await self.handle_forward_msg(msg_list)
                        seg = ret_seg
                # case "xml":
                #     pass
                case "json":
                    json_data = json.loads(html.unescape(data.get("data")))
                    detail = next(iter(json_data.get("meta", {}).values()))
                    title = detail.get("title", "")
                    desc = detail.get("desc", "")
                    tag = f"({detail.get("desc", "")})"
                    seg = Seg(type="text", data=f"分享<小程序[{title}]:{desc}{tag}>")
                case "file":
                    file = data.get("file")
                    seg = Seg(type="text", data=f"上传文件<{file}>")
                case _:
                    self.errorf(f"未知CQ码: {cq_code}")
            if seg:
                if isinstance(seg, list):
                    seg_message += seg
                else:
                    seg_message.append(seg)
            msg = msg.replace(cq_code, "", 1)
        if msg:
            seg_message.append(Seg(type="text", data=msg))
        return seg_message

    async def handle_forward_msg(self, msg_list: list) -> Seg | None:
        """处理转发消息"""
        async def process_forward_message(msg_list: list, layer: int) -> Seg:
            """解析转发消息"""
            if msg_list is None:
                return None
            seg_list: List[Seg] = []
            process_count = 0
            for sub_msg in msg_list:
                sub_msg: dict
                sender_info: dict = sub_msg.get("sender")
                user_nickname: str = sender_info.get("nickname", "QQ用户")
                user_nickname_str = f"【{user_nickname}】:"
                message_of_sub_message_list: List[Dict[str, Any]] = sub_msg.get("message")
                if not message_of_sub_message_list:
                    continue
                message_of_sub_message = message_of_sub_message_list[0]
                if message_of_sub_message.get("type") == "forward":
                    if layer >= 3:
                        full_seg_data = Seg(type="text", data=("--" * layer) + f"【{user_nickname}】:【转发消息】\n",)
                    else:
                        sub_message_data = message_of_sub_message.get("data")
                        if not sub_message_data:
                            continue
                        contents = sub_message_data.get("content")
                        seg_data = await process_forward_message(contents, layer + 1)
                        process_count += 1
                        head_tip = Seg(type="text", data=("--" * layer) + f"【{user_nickname}】: 合并转发消息内容：\n",)
                        full_seg_data = Seg(type="seglist", data=[head_tip, seg_data])
                    seg_list.append(full_seg_data)
                elif message_of_sub_message.get("type") == "text":
                    sub_message_data = message_of_sub_message.get("data")
                    if not sub_message_data:
                        continue
                    text_message = sub_message_data.get("text")
                    seg_data = Seg(type="text", data=f"{text_message}\n")
                    data_list: List[Any] = [Seg(type="text", data=("--" * layer) + user_nickname_str), seg_data]
                    seg_list.append(Seg(type="seglist", data=data_list))
                elif message_of_sub_message.get("type") == "image":
                    process_count += 1
                    image_data = message_of_sub_message.get("data")
                    sub_type = image_data.get("sub_type")
                    image_url = image_data.get("url")
                    data_list: List[Any] = []
                    if sub_type == 0:
                        if process_count > 5:
                            seg_data = Seg(type="text", data="[图片]\n")
                        else:
                            img_base64 = await self.get_image_base64(image_url)
                            seg_data = Seg(type="image", data=f"{img_base64}\n")
                    else:
                        if process_count > 3:
                            seg_data = Seg(type="text", data="[表情包]\n")
                        else:
                            img_base64 = await self.get_image_base64(image_url)
                            seg_data = Seg(type="emoji", data=f"{img_base64}\n")
                    if layer > 0:
                        data_list = [Seg(type="text", data=("--" * layer) + user_nickname_str), seg_data]
                    else:
                        data_list = [Seg(type="text", data=user_nickname_str), seg_data]
                    full_seg_data = Seg(type="seglist", data=data_list)
                    seg_list.append(full_seg_data)
            return Seg(type="seglist", data=seg_list)

        return await process_forward_message(msg_list, 0)

    async def send_to_maim(self, msg: MessageBase) -> bool:
        """发送消息到MaiMBot"""
        try:
            if len(msg.message_segment.data) == 0:
                return False
            if msg.message_segment:
                simple_msg = re.sub(
                    r"type='(image|emoji)',\s?data='.*?'",
                    r"type='\1', data='Base64File'",
                    str(msg.message_segment.data)
                )
                self.printf(f"{Fore.GREEN}[TO] {Fore.RESET}{simple_msg}")
            send_status = await self.router.send_message(msg)
            if not send_status:
                raise RuntimeError("路由未正确配置或连接异常")
            return send_status
        except Exception:
            self.errorf(f"请检查与MaiMBot之间的连接, 发送消息失败: {traceback.format_exc()}")

    async def construct_message(self) -> MessageBase:
        """根据平台事件构造标准 MessageBase"""
        user_info = UserInfo(
            platform=self.config["platform"],
            user_id=self.event.user_id,
            user_nickname=self.event.user_name,
            user_cardname=self.event.user_card,
        )
        group_info = None
        if self.event.group_id:
            group_info = GroupInfo(
                platform=self.config["platform"],
                group_id=self.event.group_id,
                group_name=self.event.group_name,
            )
        format_info: FormatInfo = FormatInfo(
            content_format=["text", "image", "emoji", "voice"],
            accept_format=[
                "text",
                "image",
                "emoji",
                "reply",
                "voice",
                "command",
                "voiceurl",
                "music",
                "videourl",
                "file",
            ],
        )
        message_info = BaseMessageInfo(
            platform=self.config["platform"],
            message_id=self.event.msg_id,
            time=time.time(),
            user_info=user_info,
            group_info=group_info,
            format_info=format_info,
        )
        seg_message: List[Seg] = await self.handle_msg(self.event.raw)
        message_segment = Seg(type="seglist", data=seg_message)
        return MessageBase(
            message_info=message_info,
            message_segment=message_segment,
            raw_message=self.event.msg,
        )

    async def get_image_base64(self, url: str, timeout: str=3, max_retries: str=3) -> str:
        """获取图片/表情包的Base64"""
        for attempt in range(max_retries):
            try:
                response = await httpx.AsyncClient().get(url, timeout=timeout)
                if response.status_code != 200:
                    raise httpx.HTTPError(response.text)
                return base64.b64encode(response.content).decode("utf-8")
            except httpx.TimeoutException:
                self.printf(f"请求图片超时重试 {attempt + 1}/{max_retries}")
                if attempt + 1 == max_retries:
                    raise

    def get_image_format(self, data: str) -> str:
        """
        从Base64编码的数据中确定图片的格式
        Parameters:
            raw_data: str: Base64编码的图片数据
        Returns:
            format: str: 图片的格式（例如 'jpeg', 'png', 'gif'）
        """
        image_bytes = base64.b64decode(data)
        return Image.open(io.BytesIO(image_bytes)).format.lower()

    def convert_image_to_gif(self, image_base64: str) -> str:
        """
        将Base64编码的图片转换为GIF格式
        Parameters:
            image_base64: str: Base64编码的图片数据
        Returns:
            str: Base64编码的GIF图片数据
        """
        if self.robot.config.is_debug:
            self.warnf("转换图片为GIF格式")
        try:
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="GIF")
            output_buffer.seek(0)
            return base64.b64encode(output_buffer.read()).decode("utf-8")
        except Exception as e:
            self.errorf(f"图片转换为GIF失败: {e}")
            return image_base64

    @via(
        lambda self: self.at_or_private()
        and self.au(1)
        and self.match(r"^(开启|启用|打开|记录|启动|关闭|禁用|取消)麦麦$")
    )
    def enable_maimbot(self):
        """启用麦麦"""
        msg = ""
        if self.match(r"(开启|启用|打开|记录|启动)"):
            self.config[self.owner_id]["enable"] = True
            msg = "麦麦机器人已开启"
            self.save_config()
        elif self.match(r"(关闭|禁用|取消)"):
            self.config[self.owner_id]["enable"] = False
            msg = "麦麦机器人已关闭"
            self.save_config()
        self.reply(msg)

    @via(lambda self: self.ID in self.robot.persist_mods
         and self.config[self.owner_id]["enable"]
         and self.event.user_id not in self.config[self.owner_id].get("blacklist")
    )
    def send_maimbot(self):
        """发送至麦麦"""
        async def send_msg_task():
            msg = await self.construct_message()
            await self.send_to_maim(msg)
        self.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(send_msg_task())
        )

qq_face: dict = {
    "0": "[表情：惊讶]",
    "1": "[表情：撇嘴]",
    "2": "[表情：色]",
    "3": "[表情：发呆]",
    "4": "[表情：得意]",
    "5": "[表情：流泪]",
    "6": "[表情：害羞]",
    "7": "[表情：闭嘴]",
    "8": "[表情：睡]",
    "9": "[表情：大哭]",
    "10": "[表情：尴尬]",
    "11": "[表情：发怒]",
    "12": "[表情：调皮]",
    "13": "[表情：呲牙]",
    "14": "[表情：微笑]",
    "15": "[表情：难过]",
    "16": "[表情：酷]",
    "18": "[表情：抓狂]",
    "19": "[表情：吐]",
    "20": "[表情：偷笑]",
    "21": "[表情：可爱]",
    "22": "[表情：白眼]",
    "23": "[表情：傲慢]",
    "24": "[表情：饥饿]",
    "25": "[表情：困]",
    "26": "[表情：惊恐]",
    "27": "[表情：流汗]",
    "28": "[表情：憨笑]",
    "29": "[表情：悠闲]",
    "30": "[表情：奋斗]",
    "31": "[表情：咒骂]",
    "32": "[表情：疑问]",
    "33": "[表情： 嘘]",
    "34": "[表情：晕]",
    "35": "[表情：折磨]",
    "36": "[表情：衰]",
    "37": "[表情：骷髅]",
    "38": "[表情：敲打]",
    "39": "[表情：再见]",
    "41": "[表情：发抖]",
    "42": "[表情：爱情]",
    "43": "[表情：跳跳]",
    "46": "[表情：猪头]",
    "49": "[表情：拥抱]",
    "53": "[表情：蛋糕]",
    "56": "[表情：刀]",
    "59": "[表情：便便]",
    "60": "[表情：咖啡]",
    "63": "[表情：玫瑰]",
    "64": "[表情：凋谢]",
    "66": "[表情：爱心]",
    "67": "[表情：心碎]",
    "74": "[表情：太阳]",
    "75": "[表情：月亮]",
    "76": "[表情：赞]",
    "77": "[表情：踩]",
    "78": "[表情：握手]",
    "79": "[表情：胜利]",
    "85": "[表情：飞吻]",
    "86": "[表情：怄火]",
    "89": "[表情：西瓜]",
    "96": "[表情：冷汗]",
    "97": "[表情：擦汗]",
    "98": "[表情：抠鼻]",
    "99": "[表情：鼓掌]",
    "100": "[表情：糗大了]",
    "101": "[表情：坏笑]",
    "102": "[表情：左哼哼]",
    "103": "[表情：右哼哼]",
    "104": "[表情：哈欠]",
    "105": "[表情：鄙视]",
    "106": "[表情：委屈]",
    "107": "[表情：快哭了]",
    "108": "[表情：阴险]",
    "109": "[表情：左亲亲]",
    "110": "[表情：吓]",
    "111": "[表情：可怜]",
    "112": "[表情：菜刀]",
    "114": "[表情：篮球]",
    "116": "[表情：示爱]",
    "118": "[表情：抱拳]",
    "119": "[表情：勾引]",
    "120": "[表情：拳头]",
    "121": "[表情：差劲]",
    "123": "[表情：NO]",
    "124": "[表情：OK]",
    "125": "[表情：转圈]",
    "129": "[表情：挥手]",
    "137": "[表情：鞭炮]",
    "144": "[表情：喝彩]",
    "146": "[表情：爆筋]",
    "147": "[表情：棒棒糖]",
    "169": "[表情：手枪]",
    "171": "[表情：茶]",
    "172": "[表情：眨眼睛]",
    "173": "[表情：泪奔]",
    "174": "[表情：无奈]",
    "175": "[表情：卖萌]",
    "176": "[表情：小纠结]",
    "177": "[表情：喷血]",
    "178": "[表情：斜眼笑]",
    "179": "[表情：doge]",
    "181": "[表情：戳一戳]",
    "182": "[表情：笑哭]",
    "183": "[表情：我最美]",
    "185": "[表情：羊驼]",
    "187": "[表情：幽灵]",
    "201": "[表情：点赞]",
    "212": "[表情：托腮]",
    "262": "[表情：脑阔疼]",
    "263": "[表情：沧桑]",
    "264": "[表情：捂脸]",
    "265": "[表情：辣眼睛]",
    "266": "[表情：哦哟]",
    "267": "[表情：头秃]",
    "268": "[表情：问号脸]",
    "269": "[表情：暗中观察]",
    "270": "[表情：emm]",
    "271": "[表情：吃 瓜]",
    "272": "[表情：呵呵哒]",
    "273": "[表情：我酸了]",
    "277": "[表情：汪汪]",
    "281": "[表情：无眼笑]",
    "282": "[表情：敬礼]",
    "283": "[表情：狂笑]",
    "284": "[表情：面无表情]",
    "285": "[表情：摸鱼]",
    "286": "[表情：魔鬼笑]",
    "287": "[表情：哦]",
    "289": "[表情：睁眼]",
    "293": "[表情：摸锦鲤]",
    "294": "[表情：期待]",
    "295": "[表情：拿到红包]",
    "297": "[表情：拜谢]",
    "298": "[表情：元宝]",
    "299": "[表情：牛啊]",
    "300": "[表情：胖三斤]",
    "302": "[表情：左拜年]",
    "303": "[表情：右拜年]",
    "305": "[表情：右亲亲]",
    "306": "[表情：牛气冲天]",
    "307": "[表情：喵喵]",
    "311": "[表情：打call]",
    "312": "[表情：变形]",
    "314": "[表情：仔细分析]",
    "317": "[表情：菜汪]",
    "318": "[表情：崇拜]",
    "319": "[表情： 比心]",
    "320": "[表情：庆祝]",
    "323": "[表情：嫌弃]",
    "324": "[表情：吃糖]",
    "325": "[表情：惊吓]",
    "326": "[表情：生气]",
    "332": "[表情：举牌牌]",
    "333": "[表情：烟花]",
    "334": "[表情：虎虎生威]",
    "336": "[表情：豹富]",
    "337": "[表情：花朵脸]",
    "338": "[表情：我想开了]",
    "339": "[表情：舔屏]",
    "341": "[表情：打招呼]",
    "342": "[表情：酸Q]",
    "343": "[表情：我方了]",
    "344": "[表情：大怨种]",
    "345": "[表情：红包多多]",
    "346": "[表情：你真棒棒]",
    "347": "[表情：大展宏兔]",
    "349": "[表情：坚强]",
    "350": "[表情：贴贴]",
    "351": "[表情：敲敲]",
    "352": "[表情：咦]",
    "353": "[表情：拜托]",
    "354": "[表情：尊嘟假嘟]",
    "355": "[表情：耶]",
    "356": "[表情：666]",
    "357": "[表情：裂开]",
    "392": "[表情：龙年 快乐]",
    "393": "[表情：新年中龙]",
    "394": "[表情：新年大龙]",
    "395": "[表情：略略略]",
    "😊": "[表情：嘿嘿]",
    "😌": "[表情：羞涩]",
    "😚": "[ 表情：亲亲]",
    "😓": "[表情：汗]",
    "😰": "[表情：紧张]",
    "😝": "[表情：吐舌]",
    "😁": "[表情：呲牙]",
    "😜": "[表情：淘气]",
    "☺": "[表情：可爱]",
    "😍": "[表情：花痴]",
    "😔": "[表情：失落]",
    "😄": "[表情：高兴]",
    "😏": "[表情：哼哼]",
    "😒": "[表情：不屑]",
    "😳": "[表情：瞪眼]",
    "😘": "[表情：飞吻]",
    "😭": "[表情：大哭]",
    "😱": "[表情：害怕]",
    "😂": "[表情：激动]",
    "💪": "[表情：肌肉]",
    "👊": "[表情：拳头]",
    "👍": "[表情 ：厉害]",
    "👏": "[表情：鼓掌]",
    "👎": "[表情：鄙视]",
    "🙏": "[表情：合十]",
    "👌": "[表情：好的]",
    "👆": "[表情：向上]",
    "👀": "[表情：眼睛]",
    "🍜": "[表情：拉面]",
    "🍧": "[表情：刨冰]",
    "🍞": "[表情：面包]",
    "🍺": "[表情：啤酒]",
    "🍻": "[表情：干杯]",
    "☕": "[表情：咖啡]",
    "🍎": "[表情：苹果]",
    "🍓": "[表情：草莓]",
    "🍉": "[表情：西瓜]",
    "🚬": "[表情：吸烟]",
    "🌹": "[表情：玫瑰]",
    "🎉": "[表情：庆祝]",
    "💝": "[表情：礼物]",
    "💣": "[表情：炸弹]",
    "✨": "[表情：闪光]",
    "💨": "[表情：吹气]",
    "💦": "[表情：水]",
    "🔥": "[表情：火]",
    "💤": "[表情：睡觉]",
    "💩": "[表情：便便]",
    "💉": "[表情：打针]",
    "📫": "[表情：邮箱]",
    "🐎": "[表情：骑马]",
    "👧": "[表情：女孩]",
    "👦": "[表情：男孩]",
    "🐵": "[表情：猴]",
    "🐷": "[表情：猪]",
    "🐮": "[表情：牛]",
    "🐔": "[表情：公鸡]",
    "🐸": "[表情：青蛙]",
    "👻": "[表情：幽灵]",
    "🐛": "[表情：虫]",
    "🐶": "[表情：狗]",
    "🐳": "[表情：鲸鱼]",
    "👢": "[表情：靴子]",
    "☀": "[表情：晴天]",
    "❔": "[表情：问号]",
    "🔫": "[表情：手枪]",
    "💓": "[表情：爱 心]",
    "🏪": "[表情：便利店]",
}
