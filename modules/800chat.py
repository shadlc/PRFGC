"""消息处理模块"""

import base64
import datetime
import io
import os
import re
import sqlite3
import time
import traceback

import jieba
from matplotlib import font_manager as fm
from matplotlib import pyplot as plt
from PIL import Image, ImageDraw
import numpy as np
from wordcloud import WordCloud

from src.utils import (
    Module,
    get_error,
    get_stranger_info,
    get_user_name,
    set_emoji,
    status_ok,
    via,
    get_msg,
)

class Chat(Module):
    """消息处理模块"""

    ID = "Chat"
    NAME = "消息处理模块"
    HELP = {
        2: [
            "[时间段]词云 | 生成某一时间段的词云",
            "为XXX生成[时间段]的词云 | 生成某人某一时间段的词云",
            "[时间段]复读排行榜 | 生成某一时间段的复读排行榜",
            "[QQ账号或昵称]又叫做[称号] | 记录成员的称号",
            "成员列表 | 查看曾有称号记录在案的成员列表和称号",
            "[QQ账号或昵称]曾说过: | 假装有人说过",
            "刚刚撤回了什么 | 查看上一个撤回消息内容",
            "回复表情图片并@机器人(空内容) | 将表情包转化为链接",
        ],
        1: [
            "(打开|关闭)词云 | 打开或关闭词云记录(默认关闭)",
            "词云配色 [配色代码] | 更改词云配色",
        ],
    }
    GLOBAL_CONFIG = {
        "database": "data.db",
        "font": "MiSans-Bold.ttf",
        "stopwords": "stopwords.txt",
    }
    CONV_CONFIG = {
        "wordcloud": {
            "enable": False,
            "colormap": "Set2"
        },
        "repeat_record": {
            "enable": False
        },
        "users": {
            
        }
    }

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"词云"), success=False)
    def wordcloud(self):
        """词云"""
        date_pattern = "历史|全部|今天|今日|本日|这天|昨天|昨日|前天|前日|本周|这周|此周|这个?礼拜|这个?星期|上周|上个?礼拜|上个?星期|本月|这月|次月|这个月|上个?月|今年|本年|此年|这一?年|去年|上一?年"
        if self.match(r"(开启|启用|打开|记录|启动|关闭|禁用|取消)"):
            if self.auth <= 1:
                self.wordcloud_switch()
                return
            else:
                msg = "你没有此操作的权限！"
        elif self.match(r"(主题|颜色|色彩|方案|配色)"):
            self.wordcloud_colormap()
            return
        elif result := self.match(rf"(给|为)?([^\s]*?)?\s?(生成|的)?({date_pattern})?的?词云"):
            if self.config[self.owner_id]["wordcloud"]["enable"]:
                gen_type = "all"
                if self.match(r"(今天|今日|本日|这天)"):
                    msg = "正在生成今日词云..."
                    gen_type = "today"
                elif self.match(r"(昨天|昨日)"):
                    msg = "正在生成昨天词云..."
                    gen_type = "yesterday"
                elif self.match(r"(前天|前日)"):
                    msg = "正在生成前天词云..."
                    gen_type = "before_yesterday"
                elif self.match(r"(本周|这周|此周|这个?礼拜|这个?星期)"):
                    msg = "正在生成本周词云..."
                    gen_type = "this_week"
                elif self.match(r"(上周|上个?礼拜|上个?星期)"):
                    msg = "正在生成上周词云..."
                    gen_type = "last_week"
                elif self.match(r"(本月|这月|次月|这个月)"):
                    msg = "正在生成本月词云..."
                    gen_type = "this_month"
                elif self.match(r"(上个?月)"):
                    msg = "正在生成上个月词云..."
                    gen_type = "last_month"
                elif self.match(r"(今年|本年|此年|这一?年)"):
                    msg = "正在生成今年词云..."
                    gen_type = "this_year"
                elif self.match(r"(去年|上一?年)"):
                    msg = "正在生成去年词云..."
                    gen_type = "last_year"
                else:
                    msg = "正在生成历史词云..."
                text = ""
                user_name = result.groups()[1]
                user_id = None
                if user_name:
                    user_id = self.get_uid(user_name)
                    if not user_id and user_name not in self.robot.data.keys():
                        self.reply(f"未找到关于{user_name}的消息记录")
                        return
                    elif user_name in self.robot.data.keys():
                        text = self.read_wordcloud(gen_type, user_name)
                        msg = msg.replace("正在生成", f"正在生成{user_name}内的")
                        msg += f"共{len(text.split("\n"))}条..."
                        self.printf(f"{user_name}词云共{len(text.split("\n"))}条")
                    else:
                        text = self.read_wordcloud(gen_type, self.owner_id, user_id)
                        user_name = get_user_name(self.robot, user_id)
                        msg = msg.replace("正在生成", f"正在生成{user_name}的")
                        msg += f"共{len(text.split("\n"))}条..."
                        self.printf(f"{self.owner_id}{f"内{user_id}的" if user_id else ""}词云共{len(text.split("\n"))}条")
                else:
                    text = self.read_wordcloud(gen_type, self.owner_id, user_id)
                    msg += f"共{len(text.split("\n"))}条..."
                    self.printf(f"{self.owner_id}{f"内{user_id}的" if user_id else ""}词云共{len(text.split("\n"))}条")
                if not text:
                    msg = "没有消息记录哦~"
                    self.reply(msg, reply=True)
                    return
                msg += "请耐心等待..."
                self.reply(msg, reply=True)
                set_emoji(self.robot, self.event.msg_id, 60)
                try:
                    url = self.generate_wordcloud(text)
                    msg = f"[CQ:image,file={url}]"
                except Exception:
                    self.errorf(traceback.format_exc())
                    msg = "词云生成错误！\n" + get_error()
            elif not self.config[self.owner_id]["wordcloud"]["enable"]:
                msg = "请先开启开启词云记录哦~"
            else:
                msg = "没有任何词云记录哦~"
        else:
            return
        self.success = True
        self.reply(msg, reply=True)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"复读(统计|记录|排行榜?)"), success=False)
    def repeat(self):
        """复读"""
        date_pattern = "历史|全部|今天|今日|本日|这天|昨天|昨日|前天|前日|本周|这周|此周|这个?礼拜|这个?星期|上周|上个?礼拜|上个?星期|本月|这月|次月|这个月|上个?月|今年|本年|此年|这一?年|去年|上一?年"
        if self.match(r"(开启|启用|打开|记录|启动)"):
            self.config[self.owner_id]["repeat_record"]["enable"] = True
            msg = "复读统计已开启"
            self.save_config()
        elif self.match(r"(关闭|禁用|取消)"):
            self.config[self.owner_id]["repeat_record"]["enable"] = False
            msg = "复读统计已关闭"
            self.save_config()
        elif match := self.match(rf"(生成)?({date_pattern})?的?复读(统计|记录|排行榜?)"):
            if self.config[self.owner_id]["repeat_record"]["enable"]:
                if self.match(r"(今天|今日)"):
                    gen_type = "today"
                elif self.match(r"(昨天|昨日)"):
                    gen_type = "yesterday"
                elif self.match(r"(前天|前日)"):
                    gen_type = "before_yesterday"
                elif self.match(r"(本周|这周|此周|这个?礼拜|这个?星期)"):
                    gen_type = "this_week"
                elif self.match(r"(上周|上个?礼拜|上个?星期)"):
                    gen_type = "last_week"
                elif self.match(r"(本月|这月|次月|这个月)"):
                    gen_type = "this_month"
                elif self.match(r"(上个?月)"):
                    gen_type = "last_month"
                elif self.match(r"(今年|本年|此年|这一?年)"):
                    gen_type = "this_year"
                elif self.match(r"(去年|上个?年)"):
                    gen_type = "last_year"
                else:
                    gen_type = "all"
                data = self.get_repeat_record(gen_type, self.owner_id)
                if not data or data == [[]]:
                    msg = "没有复读记录哦~"
                else:
                    msg = self.format_repeat_record(data, gen_type)
                    gen_type = match.groups()[1] or "历史"
                    self.reply_forward(self.node(msg), source=f"{gen_type}复读排行")
                    return
            else:
                msg = "请先开启复读记录哦~"
        else:
            return
        self.success = True
        self.reply(msg, reply=True)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^\s*(\s?(\S+)(说|言)(道|过)?(:|：)(\S+)\s?)+\s*$"))
    def once_said(self):
        """曾言道"""
        msg_said = re.findall(r"(\S+)(说|言)(道|过)?(:|：)(\S+)", self.event.msg)
        msg_list = []
        for said in msg_said:
            name = re.sub(r"曾?经?又?还?也?$", "", said[0])
            content = said[-1]
            uid = self.get_uid(name)
            if uid in self.config[self.owner_id]["users"]:
                name = self.config[self.owner_id]["users"][uid]["nickname"]
            elif name.isdigit():
                name = get_user_name(self.robot, name)
            if re.search(r"^(我|吾|俺|朕|孤)$", name):
                name = self.event.user_name
                uid = self.event.user_id
            msg_list.append(self.node(content, user_id=uid, nickname=name))
        if msg_list:
            self.reply_forward(msg_list, hidden=False)
        else:
            msg = "生成转发消息错误~"
            self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^(刚刚|刚才|先前)?\S*(说|撤回)了?(什么|啥)"))
    def what_recall(self):
        """撤回了什么"""
        if messages := self.robot.data.get("latest_recall",{}).get(self.owner_id):
            nodes = []
            for msg in messages:
                if msg.get("time") and time.time() - msg.get("time") > 3600:
                    continue
                user_id = msg.get("user_id")
                nickname = msg.get("sender",{}).get("nickname","")
                content = msg.get("raw_message","")
                content = re.sub(r",sub_type=\d", "", content)
                nodes.append(self.node(content, user_id=user_id, nickname=nickname))
            self.reply_forward(nodes, "撤回消息列表", hidden=False)
        else:
            self.reply("什么也没有哦~")

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^\s*\[CQ:reply,id=([^\]]+?)\]\s*$"), success=False)
    def sticker_url(self):
        """获取表情链接"""
        msg_id = self.match(r"^\s*\[CQ:reply,id=([^\]]+?)\]\s*$").groups()[0]
        reply_msg = get_msg(self.robot, msg_id)
        msg = reply_msg["data"]["message"]
        if status_ok(reply_msg) and re.match(r"^\s*\[CQ:image,([^\]]+?)\]\s*$", msg):
            _, url = re.match(r"^\s*\[CQ:image,.*file=([^,\]]+?),.*url=([^,\]]+?),.*\]\s*$", msg).groups()
            msg = f"{url}"
            self.reply(msg)
            self.success = True

    @via(
        lambda self: self.at_or_private()
        and self.au(2)
        and self.match(r"(\S+?)(又|也|同时)能?被?(称|叫)(为|做)?(\S+)$")
    )
    def set_label(self):
        """设置称号"""
        inputs = self.match(r"(\S+?)(又|也|同时)能?被?(称|叫)(为|做)?(\S+)").groups()
        name = inputs[0]
        label = inputs[-1]
        msg = "好像没有找到这个用户欸~"
        if name.isdigit():
            info = get_stranger_info(self.robot, name)
            if status_ok(info):
                nickname = info["data"]["nickname"]
                msg = f"我记住了，{nickname}人送外号: {label}！"
                self.record_user(name, nickname, label)
        elif re.search(r"^(我|吾|俺|朕|孤)$", name):
            msg = f"我记住了，{self.event.user_name}人送外号: {label}！"
            self.record_user(
                self.event.user_id, self.event.user_name, label
            )
        else:
            for uid, user in self.config[self.owner_id]["users"].items():
                if name == uid or name == user["nickname"]:
                    self.record_user(uid, name, label)
                    msg = f"我记住了，{name}人送外号: {label}！"
                    break
        self.reply(msg)

    @via(lambda self: self.at_or_private() and self.au(2) and self.match(r"^成员列表$"))
    def show_label(self):
        """成员列表"""
        msg = "========成员列表========"
        for uid, user in self.config[self.owner_id]["users"].items():
            msg += f"\nQQ: {uid}"
            msg += f"\n昵称: {user["nickname"]}"
            label = user["label"] if user["label"] else "无"
            msg += f"\n称号: {label}"
            msg += "\n======================="
        self.reply(msg)

    @via(lambda self: self.event.user_id not in self.config[self.owner_id]["users"]
         or self.event.user_name != self.config[self.owner_id]["users"].get(self.event.user_id,{}).get("nickname",""), success=False)
    def z_record_user(self):
        """用户记录"""
        self.record_user(self.event.user_id, self.event.user_name)

    @via(lambda self: self.config[self.owner_id]["wordcloud"]["enable"], success=False)
    def z_record_msg(self):
        """聊天消息记录"""
        msg = re.sub(r"(\[|【|{)[\s\S]*(\]|】|})", "", self.event.msg)
        msg = re.sub(r"http[s]?://\S+", "", msg)
        self.store_wordcloud(
            self.owner_id,
            self.event.user_id,
            msg,
            datetime.datetime.now()
        )

    @via(lambda self: self.config[self.owner_id]["repeat_record"]["enable"]
         and str(self.data.past_message).count(f"'message': '{self.event.msg}'") > 1, success=False)
    def z_store_repeat(self):
        """复读消息记录"""
        self.store_repeat(self.owner_id, self.event.user_id, self.event.msg)

    def record_user(self, uid: str, name: str, label: str=""):
        """记录用户称号"""
        info = self.config[self.owner_id]["users"].get("uid")
        if info and info.get("label") == "":
            label = info.get("label")
        self.config[self.owner_id]["users"][uid] = {"nickname": name, "label": label}
        self.save_config()

    def get_uid(self, name):
        """使用用户名获取ID"""
        config = self.config[self.owner_id]
        if name in config["users"]:
            return name
        if name in self.robot.user_dict:
            return name
        for uid, user_name in self.robot.user_dict.items():
            if name == user_name:
                return uid
        for uid, user in config["users"].items():
            if name in (user["nickname"], user["label"]):
                return uid
        if re.search(r"^(我|吾|俺|朕|孤)$", name):
            return self.event.user_id
        if name.isdigit():
            return name
        return 0

    def init_wordcloud_db(self, conn: sqlite3.Connection):
        """确保 wordcloud 表存在。表结构：
        id, owner_id, user_id, user_name, message, timestamp
        timestamp 为整型 Unix 时间戳（秒）。
        """
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wordcloud (
                owner_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,                -- YYYYMMDD
                text TEXT,
                update_ts TEXT,
                PRIMARY KEY (owner_id, user_id, date)
            )
            """
        )
        conn.commit()

    def store_wordcloud(self, owner_id: str, user_id: str, text: str, ts = None):
        """
        将单条聊天记录按 (owner_id, user_id, date) 合并写入数据库
        """
        try:
            if not text:
                return
            if ts is None:
                ts = datetime.datetime.now()
            date = ts.strftime("%Y%m%d")
            db = self.get_data_path(self.config["database"])
            conn = sqlite3.connect(db)
            self.init_wordcloud_db(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT text FROM wordcloud WHERE owner_id=? AND user_id=? AND date=?",
                (owner_id, user_id, date),
            )
            row = cur.fetchone()
            if row and row[0]:
                new_text = row[0] + "\n" + text
                cur.execute(
                    "UPDATE wordcloud SET text=?, update_ts=? WHERE owner_id=? AND user_id=? AND date=?",
                    (new_text, ts.isoformat(), owner_id, user_id, date),
                )
            else:
                cur.execute(
                    "INSERT OR REPLACE INTO wordcloud(owner_id, user_id, date, text, update_ts) VALUES (?, ?, ?, ?, ?)",
                    (owner_id, user_id, date, text, ts.isoformat()),
                )
            conn.commit()
            conn.close()
        except Exception:
            self.errorf("保存消息记录失败:\n" + traceback.format_exc())

    def read_wordcloud(self, gen_type: str, owner_id: str, user_id: str = None):
        """读取当前会话下的所有消息并拼接为字符串返回
        gen_type 可选：today, yesterday, before_yesterday, this_week,
        last_week, this_month, last_month, this_year, last_year, all
        """
        try:
            wordcloud_db = self.get_data_path(self.config["database"])
            date_range = self.get_date_range(gen_type)

            query = "SELECT text FROM wordcloud"
            conditions = ["owner_id=?"]
            params = [owner_id]

            if user_id:
                conditions.append("user_id=?")
                params.append(user_id)

            if date_range != (None, None):
                start_date = date_range[0].strftime("%Y%m%d")
                end_date = date_range[1].strftime("%Y%m%d")
                conditions.append("date>=?")
                conditions.append("date<=?")
                params.extend([start_date, end_date])

            where_clause = " WHERE " + " AND ".join(conditions)
            query = f"{query}{where_clause} ORDER BY date ASC"

            with sqlite3.connect(wordcloud_db) as conn:
                self.init_wordcloud_db(conn)
                cur = conn.cursor()
                cur.execute(query, params)
                rows = cur.fetchall()
            if not rows:
                return ""
            texts = [r[0] for r in rows if r[0]]
            return "\n".join(texts)
        except Exception:
            self.errorf(traceback.format_exc())
            return ""

    def get_date_range(self, type_name: str | None):
        """获取指定区间的日期"""
        today = datetime.date.today()
        if type_name == "all":
            return None, None
        if type_name == "today":
            s = e = today
        elif type_name == "yesterday":
            s = e = today - datetime.timedelta(days=1)
        elif type_name == "before_yesterday":
            s = e = today - datetime.timedelta(days=2)
        elif type_name == "this_week":
            start = today - datetime.timedelta(days=today.isoweekday() - 1)
            end = today
            s, e = start, end
        elif type_name == "last_week":
            this_monday = today - datetime.timedelta(days=today.isoweekday() - 1)
            start = this_monday - datetime.timedelta(days=7)
            end = start + datetime.timedelta(days=6)
            s, e = start, end
        elif type_name == "this_month":
            s = today.replace(day=1)
            e = today
        elif type_name == "last_month":
            first = today.replace(day=1)
            last_month_end = first - datetime.timedelta(days=1)
            s = last_month_end.replace(day=1)
            e = last_month_end
        elif type_name == "this_year":
            s = today.replace(month=1, day=1)
            e = today
        elif type_name == "last_year":
            s = today.replace(month=1, day=1).replace(year=today.year - 1)
            e = s.replace(month=12, day=31)
        else:
            return None, None
        return s, e

    def generate_wordcloud(self, text: str):
        """生成词云图片并返回 base64 URI(base64://...)"""

        stopwords = set()
        stopwords_path = self.get_data_path(self.config["stopwords"])
        try:
            with open(stopwords_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f]
        except FileNotFoundError as e:
            raise FileNotFoundError(f"未找到可用的停词表: {e.filename}") from e
        stopwords = set(lines)
        words = jieba.lcut(text)
        filtered = []
        for w in words:
            w = w.strip()
            if not w:
                continue
            if w in stopwords:
                continue
            if re.fullmatch(r"[\s\W_]+", w):
                continue
            filtered.append(w)
        if not filtered:
            raise RuntimeError("分词后没有有效词语")

        width = height = 3000
        wc_text = " ".join(filtered)
        wc_kwargs = {
            "width": width,
            "height": height,
            "background_color": "white",
            "max_words": 300,
            "collocations": False,
            "prefer_horizontal": 0.9,
        }
        
        # 主题
        colormap = self.config[self.owner_id]["wordcloud"]["colormap"]
        if colormap:
            wc_kwargs["colormap"] = colormap

        # 字体
        font_path = self.get_data_path(self.config["font"])
        if not os.path.exists(font_path):
            font_path = ""
            candidates = ["SimHei", "SimSun", "Microsoft YaHei", "STHeiti",
                          "Songti", "NotoSansCJK", "PingFang"]
            for font in sorted(fm.findSystemFonts()):
                for name in candidates:
                    if name.lower() in font.lower():
                        font_path = font
                        break
                if font_path:
                    break
        if font_path:
            wc_kwargs["font_path"] = font_path
            self.printf(f"词云字体: {font_path}")

        # 蒙版
        img = Image.new("L", (width, height), 255)
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((100,100,width-100,height-100), radius=500, fill=0)
        mask = np.array(img)
        wc_kwargs["mask"] = mask

        wc = WordCloud(**wc_kwargs)
        wc.generate(wc_text)
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=400)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"base64://{img_base64}"

    def wordcloud_switch(self):
        """打开或关闭词云"""
        msg = ""
        if self.match(r"(开启|启用|打开|记录|启动)"):
            self.config[self.owner_id]["wordcloud"]["enable"] = True
            msg = "词云记录已开启"
        elif self.match(r"(关闭|禁用|取消)"):
            self.config[self.owner_id]["wordcloud"]["enable"] = False
            msg = "词云记录已关闭"
        self.save_config()
        self.reply(msg)

    def wordcloud_colormap(self):
        """更改词云配色"""
        if self.match(r"#(\S+)"):
            colormap = self.match(r"#(\S+)").groups()[0]
            self.config[self.owner_id]["wordcloud"]["colormap"] = colormap
            self.save_config()
            msg = "词云配色设置成功！"
        else:
            msg = ("请使用[#配色代码]来设置词云的配色主题,例如：“词云主题 #Pastel2”")
            self.reply(msg)
            msg = "配色代码如下"
            for i in self.colormaps_to_img():
                msg += f"[CQ:image,file={i}]"
        self.reply(msg)

    def colormaps_to_img(self, batch_size=200, width=300, height_per_map=40, dpi=50):
        """系统内colormap生成图片"""
        colormaps = plt.colormaps()
        n = len(colormaps)
        n_batches = (n + batch_size - 1) // batch_size
        base64_images = []

        for i in range(n_batches):
            batch = colormaps[i*batch_size:(i+1)*batch_size]
            height = height_per_map * len(batch)
            _, axes = plt.subplots(len(batch), 1, figsize=(width/dpi, height/dpi), dpi=dpi)

            for ax, name in zip(axes, batch):
                gradient = np.linspace(0, 1, 256).reshape(1, -1)
                ax.imshow(gradient, aspect="auto", cmap=plt.get_cmap(name))
                ax.set_axis_off()
                ax.set_title(name, fontsize=10, loc="center")

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format="jpg", bbox_inches="tight", pad_inches=0, dpi=dpi*4)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode("utf-8")
            base64_images.append(f"base64://{img_base64}")
            plt.close()

        return base64_images

    def init_repeat_db(self, conn: sqlite3.Connection):
        """确保 repeat 表存在。表结构：
        id, owner_id, user_id, user_name, message, timestamp
        timestamp 为整型 Unix 时间戳（秒）。
        """
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS repeat (                   -- 复读表
                owner_id TEXT,                      -- 所属ID
                user_id INTEGER,                    -- 用户ID
                date TEXT NOT NULL,                 -- YYYYMMDD
                text TEXT,                          -- 复读内容
                update_ts TEXT                      -- 时间戳
            );
        """)
        conn.commit()

    def store_repeat(self, owner_id: str, user_id: str, text: str, ts = None):
        """存储复读记录"""
        try:
            if not text:
                return
            if ts is None:
                ts = datetime.datetime.now()
            date = ts.strftime("%Y%m%d")
            db_path = self.get_data_path(self.config["database"])
            conn = sqlite3.connect(db_path)
            self.init_repeat_db(conn)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO repeat VALUES (?, ?, ?, ?, ?);",
                (
                    owner_id,
                    user_id,
                    date,
                    text,
                    ts.isoformat(),
                )
            )
            conn.commit()
            conn.close()
        except Exception:
            self.errorf("保存复读记录失败:\n" + traceback.format_exc())

    def get_repeat_record(self, gen_type: str, owner_id: str):
        """获取复读记录"""
        db_path = self.get_data_path(self.config["database"])
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM repeat"
        params = [owner_id]
        conditions = ["OWNER_ID=?"]

        date_range = self.get_date_range(gen_type)
        if date_range != (None, None):
            start_date = date_range[0].strftime("%Y%m%d")
            end_date = date_range[1].strftime("%Y%m%d")
            conditions.append("date>=?")
            conditions.append("date<=?")
            params.extend([start_date, end_date])

        where_clause = " WHERE " + " AND ".join(conditions)
        query = f"{query}{where_clause} ORDER BY date ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def format_repeat_record(self, data: list, gen_type: str):
        """格式化复读排行榜"""
        date_dict = {
            "today": "今日",
            "yesterday": "昨天",
            "before_yesterday": "前天",
            "this_week": "本周",
            "last_week": "上周",
            "this_month": "本月",
            "last_month": "上个月",
            "this_year": "今年",
            "last_year": "去年",
            "all": "历史",
        }
        type_text = date_dict[gen_type] if gen_type in date_dict else "历史"
        msg = "%ROBOT_NAME%复读统计开始啦~"
        total_repeat_times = len(data)
        msg += f"\n{type_text}共复读{total_repeat_times}次"
        text_count_dict = {}
        for item in data:
            if item[3] in text_count_dict:
                text_count_dict[item[3]] += 1
            else:
                text_count_dict[item[3]] = 1
        text_sorted = sorted(text_count_dict.items(), key=lambda x: x[1], reverse=True)
        msg += f"\n\n其中，被复读最多次的是“{text_sorted[0][0]}”，共被复读了{text_sorted[0][1]}次"
        user_count_dict = {}
        for item in data:
            if item[1] in user_count_dict:
                user_count_dict[item[1]] += 1
            else:
                user_count_dict[item[1]] = 1
        user_sorted = sorted(user_count_dict.items(), key=lambda x: x[1], reverse=True)
        mvp_dict = {}
        for item in data:
            if user_sorted[0][0] != item[1]:
                continue
            if item[3] in mvp_dict:
                mvp_dict[item[3]] += 1
            else:
                mvp_dict[item[3]] = 1
        mvp_dict = sorted(mvp_dict.items(), key=lambda x: x[1], reverse=True)
        if not self.event.group_id:
            return msg
        msg += f"\n\n[CQ:at,qq={user_sorted[0][0]}]复读的最勤快了，把“{mvp_dict[0][0]}”复读了{mvp_dict[0][1]}次"
        if total_repeat_times >= 20 and total_repeat_times < 50 and len(text_sorted) >= 3:
            msg += "\n\n此外，这是复读次数排行榜:"
            msg += f"\n第一名: {text_sorted[0][0]}, 计数{text_sorted[0][1]}次"
            msg += f"\n第二名: {text_sorted[1][0]}, 计数{text_sorted[1][1]}次"
            msg += f"\n第三名: {text_sorted[2][0]}, 计数{text_sorted[2][1]}次"
        elif total_repeat_times >= 50 and len(text_sorted) >= 5:
            msg += "\n\n此外，这是复读次数排行榜:"
            msg += f"\n第一名: {text_sorted[0][0]}, 计数{text_sorted[0][1]}次"
            msg += f"\n第二名: {text_sorted[1][0]}, 计数{text_sorted[1][1]}次"
            msg += f"\n第三名: {text_sorted[2][0]}, 计数{text_sorted[2][1]}次"
            msg += f"\n第四名: {text_sorted[3][0]}, 计数{text_sorted[3][1]}次"
            msg += f"\n第五名: {text_sorted[4][0]}, 计数{text_sorted[4][1]}次"
            msg += "\n\n这是成员复读排行榜:"
            msg += f"\n第一名: [CQ:at,qq={user_sorted[0][0]}], 计数{user_sorted[0][1]}次"
            msg += f"\n第二名: [CQ:at,qq={user_sorted[1][0]}], 计数{user_sorted[1][1]}次"
            msg += f"\n第三名: [CQ:at,qq={user_sorted[2][0]}], 计数{user_sorted[2][1]}次"
            msg += f"\n第四名: [CQ:at,qq={user_sorted[3][0]}], 计数{user_sorted[3][1]}次"
            msg += f"\n第五名: [CQ:at,qq={user_sorted[4][0]}], 计数{user_sorted[4][1]}次"
        return msg
