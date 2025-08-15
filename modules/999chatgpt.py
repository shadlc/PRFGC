"""ChatGPT模块处理"""

import re

from src.api import get_msg
from src.utils import Module, via

class ChatGPT(Module):
    """基础消息处理模块"""

    ID = "ChatGPT"
    NAME = "ChatGPT模块"
    HELP = {
        3: [
            "以#开头或者直接@我发送消息就能和我聊天啦~",
            "重置会话 | 重置当前会话记忆",
        ]
    }
    CONFIG = "chatgpt.json"
    GLOBAL_CONFIG = {
        "base_url": "",
        "token": "",
        "model": "",
    }
    CONV_CONFIG = None

    def chatgpt(self):
        if re.search(r"\[CQ:reply,id=(.*)\]", self.event.msg):
            msg_id = re.search(r"\[CQ:reply,id=([^\]]+)\]", self.event.msg).groups()[0]
            reply_msg_data = get_msg(self.robot, {"message_id": msg_id})["data"]
            sender = ""
            if reply_msg_data:
                reply_msg = re.sub(
                    r"\[CQ:(json|xml|forward|reply),.*\]",
                    "",
                    reply_msg_data.get("message"),
                )
                sender = reply_msg_data.get("sender")
            latest_msg = get_chatgpt_latest_ask(f"{self.robot.self_id}{self.owner_id}")
            latest_msg = (
                latest_msg if isinstance(latest_msg, str) else latest_msg[0]["text"]
            )
            if not latest_msg or reply_msg_data and latest_msg not in reply_msg:
                only_text = re.sub(r"\[CQ:image.*\]", "", reply_msg)
                only_text = text_preprocess(only_text)
                image_url = re.findall(r"\[CQ:image.*?url=([^;]*)", reply_msg)
                all_content = [{"type": "text", "text": only_text}] + [
                    {"type": "image_url", "image_url": {"url": i}} for i in image_url
                ]
                if sender.get("user_id") == self.robot.self_id:
                    content = [{"role": "assistant", "content": all_content}]
                else:
                    nick_name = sender.get("nickname")
                    all_content[0]["text"] = f"({nick_name}说)" + all_content[0]["text"]
                    content = [{"role": "user", "content": all_content}]
                add_chatgpt_convo(content, f"{self.robot.self_id}{self.owner_id}")

        only_text = re.sub(r"\[CQ:image.*\]", "", self.event.msg)
        only_text = text_preprocess(only_text)
        image_url = re.findall(r"\[CQ:image.*?url=([^;]*)", self.event.msg)
        all_content = [{"type": "text", "text": only_text}] + [
            {"type": "image_url", "image_url": {"url": i}} for i in image_url
        ]
        msg = get_chatgpt(all_content, self.event.user_name, self.owner_id)
        msg = msg if msg else "[CHATGPT] 返回为空"

        if re.search(r"\[paint_prompt:.+\]", msg):
            prompt = re.search(r"\[paint_prompt:(.+)\]", msg).groups()[0]
            prompt = prompt.replace(",", "%2C")
            image = f"[CQ:image,file=https://image.pollinations.ai/prompt/{prompt}]"
            msg = re.sub(r"\[paint_prompt:(.+)\]", "", msg)
            self.reply(self.reply_code() + msg + image)
        else:
            self.reply(self.reply_code() + msg)

    @via(lambda self: self.at_or_private() and self.auth<=2
         and re.search(r"^重置(会话|对话|聊天)$", self.event.msg))
    def reset_conv(self, auth):
        if not self.event.group_id or auth <= 2:
            msg = reset_chatgpt_conv(f"{self.robot.self_id}{self.owner_id}")
        else:
            msg = "您无权限这样做！"
        self.reply(msg)

    def reply_code(self):
        if len(str(self.event.msg_id)) > 6:
            msg = f"[CQ:reply,id={self.event.msg_id}]"
        else:
            msg = ""
        return msg


# def text_preprocess(text):
#     text = re.sub(r"\[CQ:(json|xml|forward|reply),.*\]", "", text)
#     if re.search(r"\[CQ:record,.*url=(.*)\]", text):
#         text = re.sub(r"\[CQ:record.*\]", "[语言]", text)
#     return text


# def get_chatgpt(content, user_name=None, chat_id="temp"):
#     if user_name:
#         message = f"({user_name}对你说){content}"
#     else:
#         message = content
#     post_json = {
#         "message": message,
#         "user": str(user_name),
#         "bot_id": str(self.robot.self_id),
#         "chat_id": str(chat_id),
#     }
#     if is_debug:
#         info(f"调用 ChatGPT API (/chat)：{post_json}")
#     dat = json.dumps(post_json)
#     response = ""
#     try:
#         if user_name:
#             response = requests.post(
#                 config["chatgpt_url"] + "/chat",
#                 headers={"Content-Type": "application/json"},
#                 data=dat,
#             ).json()
#         else:
#             response = requests.post(
#                 config["chatgpt_url"] + "/temp_chat",
#                 headers={"Content-Type": "application/json"},
#                 data=dat,
#             ).json()
#     except:
#         return "[ChatGPT] 连接故障！"
#     if "response" not in response:
#         return json.dumps(response)
#     else:
#         response = html.unescape(response["response"])
#         return response


# self.robot.func["get_chatgpt"] = get_chatgpt


# def get_chatgpt_latest_ask(convo_id):
#     post_json = {"convo_id": convo_id}
#     if self.robot.is_debug:
#         info(f"调用 ChatGPT API (/latest)：{post_json}")
#     dat = json.dumps(post_json)
#     response = ""
#     try:
#         response = requests.post(
#             config["chatgpt_url"] + "/latest",
#             headers={"Content-Type": "application/json"},
#             data=dat,
#         )
#     except:
#         return ""
#     if response.status_code == 200:
#         response = response.json()
#         return response["response"]
#     else:
#         return ""


# def add_chatgpt_convo(content, convo_id):
#     post_json = {"content": content, "convo_id": convo_id}
#     if self.robot.is_debug:
#         info(f"调用 ChatGPT API (/add)：{post_json}")
#     dat = json.dumps(post_json)
#     response = ""
#     try:
#         response = requests.post(
#             config["chatgpt_url"] + "/add",
#             headers={"Content-Type": "application/json"},
#             data=dat,
#         )
#     except:
#         return False
#     if response.status_code == 200:
#         return True
#     else:
#         return False


# def reset_chatgpt_conv(convo_id):
#     post_json = {"convo_id": convo_id}
#     if self.robot.is_debug:
#         info(f"调用 ChatGPT API (/reset)：{post_json}")
#     dat = json.dumps(post_json)
#     response = ""
#     try:
#         response = requests.post(
#             config["chatgpt_url"] + "/reset",
#             headers={"Content-Type": "application/json"},
#             data=dat,
#         )
#     except Exception as e:
#         return f"[ChatGTP] 重置失败！错误原因：{e}"
#     if response.status_code == 200:
#         return "[ChatGTP] 已重置会话！"
#     if response.status_code == 412:
#         return "[ChatGTP] 重置失败！您的会话为空！"
#     else:
#         return f"[ChatGTP] 重置失败！错误码：{response.status_code}"


# def get_stable_diffusion(gen_json):
#     try:
#         response = requests.post(
#             url=f"{config['webui_url']}{config['webui_api_path']}", json=gen_json
#         )
#     except Exception as e:
#         return "[未开启AI画图，请联系管理员开启！]"
#     if response.status_code == 504:
#         return f"[未开启AI画图，请联系管理员开启！]"
#     elif response.status_code != 200:
#         return f"[AI画图连接故障：{response.text}]"

#     r = response.json()

#     image = r["images"][0].split(",", 1)[0]
#     image_info = json.loads(r["info"])
#     return f"[CQ:image,file=base64://{image}]"


# def temp_chatgpt(text):
#     post_json = {"message": f"{text}", "bot_id": str(self.robot.self_id)}
#     if self.robot.is_debug:
#         info(f"调用 ChatGPT API (/temp_chat)：{post_json}")
#     dat = json.dumps(post_json)
#     try:
#         response = requests.post(
#             config["chatgpt_url"] + "/temp_chat",
#             headers={"Content-Type": "application/json"},
#             data=dat,
#         ).json()
#         response = html.unescape(response["response"])
#     except:
#         response = ""
#     return response
