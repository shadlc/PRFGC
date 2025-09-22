"""跑团功能模块"""
import json
import random
import datetime
import sqlite3
import re
from src.utils import Module, via, get_user_name

class RPG(Module):
    """跑团功能模块"""
    ID = "RPG"
    NAME = "跑团功能模块"
    HELP = {
        0: [
            "本模块为CoC风格跑团模块，无需使用@，而是.开头调用",
        ],
        2: [
            ".r | 掷6面骰",
            ".r[dice表达式] | 掷骰（如 r1d20+5, r3d6）",
            ".rXdY | 掷X个Y面骰，X不填入默认为1",
            ".ra [宾语][概率][主语] | 掷100面骰进行事件判定",
            ".sr A B C D E F | 定义一个特殊6面骰，六个面的点数分别是ABCDEF",
            ".srv | 查看当前特殊6面骰",
            ".srXd | 掷X个特殊6面骰，X不填入默认为1",
            ".ra [技能/属性] | 检定（如 ra 力量）",
            ".ri[+修正] | 掷先攻（如 ri+2）",
            ".hp±数字 | 修改当前 HP（如 hp-5）",
            ".mp±数字 | 修改当前 MP（如 mp-3）",
            ".pc new [名字] | 新建人物卡",
            ".pc auto | 自动生成符合规则的人物卡",
            ".pc set [属性]=值 | 设置属性（如 pc set 力量=60）",
            ".pc show [@某人] | 查看自己或他人人物卡",
            ".pc del | 删除人物卡",
            ".st [技能名] [值] | 快速设置技能值",
            ".stlist | 显示标准调查员技能列表",
            ".jrrp | 今日人品（1~100）",
            ".coin | 掷硬币（正/反）",
            ".sc [san值变化] | 理智检定（如 sc 1/1d6）",
            ".coc | 显示CoC相关帮助信息",
            ".help | 显示模块帮助信息",
            ".log | 查看最近的骰子记录",
            ".team create [队伍名] | 创建队伍",
            ".team join [队伍名] | 加入队伍",
            ".team leave | 离开队伍",
            ".team info | 查看队伍信息",
            ".team list | 查看所有队伍",
            ".battle start | 开始战斗（需要队伍）",
            ".battle end | 结束战斗",
            ".battle status | 查看战斗状态",
            ".battle next | 推进到下一回合",
            ".init | 查看先攻列表",
        ]
    }

    # CoC 标准技能列表
    COC_SKILLS = {
        "战斗技能": ["斗殴", "闪避", "手枪", "步枪", "弓术", "矛术", "剑术"],
        "调查技能": ["侦查", "聆听", "潜行", "追踪", "图书馆使用", "考古学", "历史", "神秘学"],
        "语言技能": ["母语", "英语", "法语", "德语", "拉丁语", "中文", "日语"],
        "其他技能": ["心理学", "急救", "医学", "魅惑", "说服", "恐吓", "信誉", "驾驶", "机械维修", "电子学"]
    }

    # 疯狂症状表
    MADNESS_SYMPTOMS = [
        "失忆：调查员会发现自己只记得最后身处的安全地点，却没有任何来到这里的记忆。",
        "假性残疾：调查员陷入了心理性的失明，失聪以及躯体缺失感中。",
        "暴力倾向：调查员陷入了六亲不认的暴力行为中，对周围的敌人与友方进行着无差别的攻击。",
        "偏执：调查员陷入了严重的偏执妄想之中，觉得其他人都在策划阴谋陷害他。",
        "人际依赖：调查员因为一些原因而将他人误认为了自己重要的人。",
        "昏厥：调查员当场昏倒，并需要1D10轮才能醒来。",
        "逃避行为：调查员会用任何的手段试图逃离当前所在之处。",
        "竭嘶底里：调查员表现出大笑，哭泣，嘶吼，害怕等的极端情绪表现。",
        "恐惧：调查员通过一次D100或者由守秘人选择，来从恐惧症状表中选择一个恐惧源。",
        "躁狂：调查员通过一次D100或者由守秘人选择，来从躁狂症状表中选择一个躁狂的诱因。"
    ]

    GLOBAL_CONFIG = {
        "database": "data.db",
        "max_log_entries": 100  # 最大日志条目数
    }
    CONV_CONFIG = {
        "teams": {},
        "battles": {},
        "users": {},
        "special_dice": {},
        "logs": []  # 新增日志记录
    }

    def init_rpg_db(self, conn: sqlite3.Connection):
        """确保 RPG 表存在"""
        cur = conn.cursor()
        # 角色卡表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                owner_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                name TEXT,
                data TEXT,
                update_ts TEXT,
                PRIMARY KEY (owner_id, user_id)
            )
        """)
        # 战斗记录表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battles (
                owner_id TEXT NOT NULL,
                battle_id TEXT NOT NULL,
                data TEXT,
                update_ts TEXT,
                PRIMARY KEY (owner_id, battle_id)
            )
        """)
        # 日志表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                owner_id TEXT NOT NULL,
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                details TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()

    def add_log(self, action, details, user_id=None):
        """添加日志记录"""
        if user_id is None:
            user_id = self.event.user_id

        log_entry = {
            "user_id": user_id,
            "action": action,
            "details": details,
            "timestamp": datetime.datetime.now().isoformat()
        }

        # 内存中的日志记录
        if "logs" not in self.config[self.owner_id]:
            self.config[self.owner_id]["logs"] = []

        self.config[self.owner_id]["logs"].append(log_entry)

        # 只保留最近的日志
        max_logs = self.config.get("max_log_entries", 100)
        if len(self.config[self.owner_id]["logs"]) > max_logs:
            self.config[self.owner_id]["logs"] = self.config[self.owner_id]["logs"][-max_logs:]

        # 数据库中的日志记录
        db_path = self.get_data_path(self.config["database"])
        conn = sqlite3.connect(db_path)
        self.init_rpg_db(conn)
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO logs (owner_id, user_id, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (self.owner_id, str(user_id), action, json.dumps(details), datetime.datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        self.save_config()

    def get_user_pc(self, user_id=None):
        """获取用户角色卡"""
        if user_id is None:
            user_id = self.event.user_id

        db_path = self.get_data_path(self.config["database"])
        conn = sqlite3.connect(db_path)
        self.init_rpg_db(conn)
        cur = conn.cursor()

        cur.execute(
            "SELECT data FROM characters WHERE owner_id=? AND user_id=?",
            (self.owner_id, str(user_id))
        )
        row = cur.fetchone()
        conn.close()

        if row and row[0]:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                self.errorf(f"用户[{user_id}]存储数据无效")
                return {}
        return {}

    def save_user_pc(self, pc_data, user_id=None):
        """保存用户角色卡"""
        if user_id is None:
            user_id = self.event.user_id

        db_path = self.get_data_path(self.config["database"])
        conn = sqlite3.connect(db_path)
        self.init_rpg_db(conn)
        cur = conn.cursor()

        cur.execute(
            "INSERT OR REPLACE INTO characters (owner_id, user_id, name, data, update_ts) VALUES (?, ?, ?, ?, ?)",
            (self.owner_id, str(user_id), pc_data.get("Name", "未命名"), json.dumps(pc_data), datetime.datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        # 记录日志
        self.add_log("save_pc", {"character": pc_data.get("Name", "未命名")}, user_id)

    def generate_coc_character(self):
        """生成符合CoC规则的角色卡"""
        # CoC 7th 属性生成规则
        attributes = {
            "STR": random.randint(15, 90),  # 力量
            "CON": random.randint(15, 90),  # 体质
            "SIZ": random.randint(15, 90),  # 体型
            "DEX": random.randint(15, 90),  # 敏捷
            "APP": random.randint(15, 90),  # 外貌
            "INT": random.randint(15, 90),  # 智力
            "POW": random.randint(15, 90),  # 意志
            "EDU": random.randint(15, 90),  # 教育
        }

        # 衍生属性
        attributes["HP"] = (attributes["CON"] + attributes["SIZ"]) // 10
        attributes["MP"] = attributes["POW"] // 5
        attributes["SAN"] = attributes["POW"]
        attributes["幸运"] = random.randint(15, 90)
        attributes["DB"] = self.calculate_db(attributes["STR"], attributes["SIZ"])

        # 基础技能点
        skill_points = attributes["EDU"] * 20 + attributes["INT"] * 10

        # 分配一些基础技能
        skills = {
            "闪避": attributes["DEX"] // 2,
            "母语": attributes["EDU"] * 5,
            "侦查": 25,
            "聆听": 20,
            "心理学": 10,
            "急救": 30,
        }

        # 消耗技能点
        available_points = skill_points - sum(skills.values())

        # 随机选择一些技能进行分配
        all_skills = []
        for category in self.COC_SKILLS.values():
            all_skills.extend(category)

        # 移除已分配的技能
        for skill in list(skills.keys()):
            if skill in all_skills:
                all_skills.remove(skill)

        # 随机分配剩余技能点
        random.shuffle(all_skills)
        for skill in all_skills[:10]:  # 分配10个额外技能
            if available_points <= 0:
                break
            points = min(random.randint(5, 30), available_points)
            skills[skill] = points
            available_points -= points

        # 合并属性和技能
        character = {**attributes, **skills}
        character["Name"] = f"调查员{random.randint(1000, 9999)}"

        return character

    def calculate_db(self, str_val, siz_val):
        """计算伤害加值"""
        total = str_val + siz_val
        if total <= 64: return "-2"
        elif total <= 84: return "-1"
        elif total <= 124: return "0"
        elif total <= 164: return "+1D4"
        elif total <= 204: return "+1D6"
        else: return "+2D6"

    @via(lambda self: self.au(2) and self.match(r"^\.help$"))
    def help(self):
        help_text = ""
        for i in range(4):
            if self.auth <= i or i == 0:
                for text in self.HELP.get(i, []):
                    help_text += f"{text}\n"
                    if i == 0:
                        help_text += "\n"
        nodes = [self.node(help_text)]
        self.reply_forward(nodes, source="跑团功能帮助")

    @via(lambda self: self.au(2) and self.match(r"^\.r[0-9dD\+\-\s]*$"))
    def roll(self):
        """掷骰子"""
        def process_dice_part(part, detail):
            """处理骰子表达式的一部分 (含正负号)"""
            if not part:
                return 0
            sign = 1
            if part.startswith('-'):
                sign = -1
                part = part[1:]
            elif part.startswith('+'):
                part = part[1:]
            # 处理骰子表达式 (NdM)
            if "d" in part.lower():
                num, sides = part.lower().split("d", 1)
                num = int(num) if num.isdigit() else 1
                sides = int(sides) if sides.isdigit() else 6
                # 限制最大值
                num = min(num, 100)
                sides = min(sides, 1000)
                rolls = [random.randint(1, sides) for _ in range(num)]
                subtotal = sum(rolls) * sign
                detail.append(f"{'-' if sign < 0 else ''}{num}d{sides}={rolls}->{subtotal}")
                return subtotal
            else:
                # 处理纯数字部分
                try:
                    val = int(part) * sign
                    detail.append(str(val))
                    return val
                except ValueError:
                    return 0

        expr = self.event.msg[2:].lower().replace(" ", "")  # 去掉前缀 ".r"
        # 默认情况 ".r"
        if not expr:
            expr = "1d6"
        try:
            detail = []
            # 用正则切割所有项 (包含符号)，保证每部分都有 ± 前缀
            parts = re.findall(r'[+-]?\d*d?\d*', expr)
            parts = [p for p in parts if p]  # 去掉空串
            total = sum(process_dice_part(part, detail) for part in parts)
            user_name = get_user_name(self.robot, self.event.user_id)
            msg = f"🎲 {user_name} 掷骰: {total}\n({', '.join(detail)})"
            # 记录日志
            self.add_log("roll", {
                "expression": expr,
                "result": total,
                "details": detail
            })
        except Exception as e:
            msg = f"骰子表达式错误: {expr}\n错误: {str(e)}"
        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.ra\s?\S*$"))
    def check(self):
        """检定（关联人物卡）和事件判定"""
        # 获取消息内容
        content = self.event.msg[3:].strip()

        # 事件判定模式 (.ra [宾语][概率][主语])
        if any(char.isdigit() for char in content):
            try:
                # 尝试解析概率值
                probability = 50  # 默认概率
                subject = ""
                object_ = ""

                # 查找数字作为概率
                parts = content.split()
                for part in parts:
                    if part.isdigit():
                        probability = min(max(int(part), 1), 100)  # 限制在1-100范围内
                        break

                # 尝试分离主语和宾语
                if " " in content:
                    non_digit_parts = [p for p in parts if not p.isdigit()]
                    if len(non_digit_parts) >= 2:
                        object_ = non_digit_parts[0]
                        subject = " ".join(non_digit_parts[1:])
                    elif non_digit_parts:
                        object_ = " ".join(non_digit_parts)

                roll = random.randint(1, 100)
                success = roll <= probability

                # 构建事件描述
                event_desc = ""
                if object_ and subject:
                    event_desc = f"{subject}进行{object_}"
                elif object_:
                    event_desc = f"进行{object_}"
                elif subject:
                    event_desc = f"{subject}进行判定"
                else:
                    event_desc = "进行判定"

                result_text = "成功" if success else "失败"
                if roll == 1:
                    result_text = "大成功"
                elif roll == 100:
                    result_text = "大失败"
                elif success and roll <= probability // 5:
                    result_text = "极难成功"
                elif success and roll <= probability // 2:
                    result_text = "困难成功"

                user_name = get_user_name(self.robot, self.event.user_id)
                msg = f"🎲 {user_name} {event_desc}: {roll}/{probability} → {result_text}"

                # 记录日志
                self.add_log("check", {
                    "type": "event",
                    "probability": probability,
                    "roll": roll,
                    "result": result_text
                })

            except Exception as e:
                msg = f"事件判定解析错误: {e}"
        else:
            # 技能检定模式
            skill = content or "未知技能"
            pc = self.get_user_pc()

            # 检查是否为标准技能但未设置
            target = pc.get(skill)
            if target is None:
                # 提供标准技能的默认值提示
                for category, skills in self.COC_SKILLS.items():
                    if skill in skills:
                        target = 0  # 设置为0，提示用户需要设置
                        break

            roll = random.randint(1, 100)

            if target is not None:
                # 进行 CoC 风格判定
                if roll == 1:
                    result = "大成功 ✅"
                elif roll == 100 or (roll > 95 and target < 50):
                    result = "大失败 ❌"
                elif roll <= target / 5:
                    result = "极难成功 ✨"
                elif roll <= target / 2:
                    result = "困难成功 👍"
                elif roll <= target:
                    result = "成功 ✔️"
                else:
                    result = "失败 ❌"
    
                user_name = get_user_name(self.robot, self.event.user_id)
                if target == 0:
                    msg = f"🎲 {user_name} {skill} 检定: {roll} (未设置{skill}，请使用 .st {skill} [数值] 设置)"
                else:
                    msg = f"🎲 {user_name} {skill} 检定: {roll} / {target} → {result}"
    
                # 记录日志
                self.add_log("check", {
                    "type": "skill",
                    "skill": skill,
                    "target": target,
                    "roll": roll,
                    "result": result
                })
            else:
                user_name = get_user_name(self.robot, self.event.user_id)
                msg = f"🎲 {user_name} {skill} 检定: {roll}（未设置人物卡属性，无法判定成败）"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.sc\s+[\d/dfF]+$"))
    def sanity_check(self):
        """理智检定"""
        try:
            content = self.event.msg[3:].strip()
            if "/" in content:
                success_loss, fail_loss = content.split("/")
            else:
                success_loss = 0
                fail_loss = content

            # 解析损失值
            def parse_loss(loss_str):
                if loss_str.isdigit():
                    return int(loss_str)
                elif "d" in loss_str.lower():
                    num, sides = loss_str.lower().split("d")
                    num = int(num) if num.isdigit() else 1
                    sides = int(sides) if sides.isdigit() else 6
                    return sum(random.randint(1, sides) for _ in range(num))
                return 0

            success_loss_val = parse_loss(success_loss)
            fail_loss_val = parse_loss(fail_loss)

            pc = self.get_user_pc()
            san = pc.get("理智", pc.get("SAN", 50))
            roll = random.randint(1, 100)

            if roll <= san:
                result = "成功"
                loss = success_loss_val
                critical = roll <= san / 5
            else:
                result = "失败"
                loss = fail_loss_val
                critical = roll >= 96

            new_san = max(0, san - loss)

            # 检查是否触发疯狂
            madness = ""
            if new_san == 0:
                madness = random.choice(self.MADNESS_SYMPTOMS)
                madness_msg = f"\n💀 理智归零！症状: {madness}"
            elif loss >= 5 or critical:
                madness = random.choice(self.MADNESS_SYMPTOMS)
                madness_msg = f"\n😵 临时疯狂！症状: {madness}"
            else:
                madness_msg = ""

            # 更新角色卡
            pc["理智"] = new_san
            pc["SAN"] = new_san
            self.save_user_pc(pc)

            user_name = get_user_name(self.robot, self.event.user_id)
            msg = f"🧠 {user_name} 理智检定: {roll}/{san} → {result}, 损失 {loss}点理智, 剩余 {new_san}{madness_msg}"

            # 记录日志
            self.add_log("sanity_check", {
                "roll": roll,
                "original_san": san,
                "new_san": new_san,
                "loss": loss,
                "result": result,
                "madness": bool(madness),
                "madness_type": "归零" if new_san == 0 else "临时" if madness else "无"
            })

        except Exception as e:
            msg = f"理智检定错误: {e}"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.st\s+\S+\s+\d+$"))
    def set_skill(self):
        """快速设置技能"""
        try:
            parts = self.event.msg[3:].strip().split()
            if len(parts) < 2:
                msg = "使用方法: .st [技能名] [值]"
            else:
                skill = parts[0]
                value = int(parts[1])
    
                if value < 0 or value > 100:
                    msg = "技能值必须在 0-100 之间"
                else:
                    pc = self.get_user_pc()
                    pc[skill] = value
                    self.save_user_pc(pc)

                    user_name = get_user_name(self.robot, self.event.user_id)
                    msg = f"📝 {user_name} 设置 {skill} = {value}"

        except ValueError:
            msg = "技能值必须是数字"
        except Exception as e:
            msg = f"设置技能错误: {e}"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.stlist$"))
    def show_skill_list(self):
        """显示标准技能列表"""
        msg = "📚 CoC 标准技能列表:\n"
        for category, skills in self.COC_SKILLS.items():
            msg += f"\n{category}:\n"
            msg += ", ".join(skills) + "\n"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.sr(?:\s+[\d\s]+)?$"))
    def set_special_dice(self):
        """设置特殊骰子"""
        try:
            # 获取参数部分
            args = self.event.msg[3:].strip().split()

            if len(args) != 6:
                msg = "❌ 需要 exactly 6 个参数来定义特殊骰子的六个面"
            else:
                # 尝试将参数转换为整数
                faces = []
                for arg in args:
                    try:
                        faces.append(int(arg))
                    except ValueError:
                        msg = f"❌ 参数 '{arg}' 不是有效的数字"
                        self.reply(msg)
                        return

                # 保存特殊骰子
                user_id = self.event.user_id
                self.config[self.owner_id]["special_dice"][user_id] = faces
                self.save_config()
                msg = f"✅ 特殊骰子设置成功: {faces}"
    
                # 记录日志
                self.add_log("set_special_dice", {"faces": faces})

        except Exception as e:
            msg = f"设置特殊骰子时出错: {e}"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.srv$"))
    def view_special_dice(self):
        """查看特殊骰子"""
        user_id = self.event.user_id
        if user_id in self.config[self.owner_id]["special_dice"]:
            faces = self.config[self.owner_id]["special_dice"][user_id]
            msg = f"🎲 您的特殊骰子: {faces}"
        else:
            msg = "❌ 您还没有设置特殊骰子，请使用 .sr 命令设置"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.sr\d*$"))
    def roll_special_dice(self):
        """掷特殊骰子"""
        user_id = self.event.user_id

        if user_id not in self.config[self.owner_id]["special_dice"]:
            msg = "❌ 您还没有设置特殊骰子，请使用 .sr 命令设置"
            self.reply(msg)
            return

        # 获取骰子数量
        expr = self.event.msg[2:]  # 去掉 ".sr"
        if expr:
            try:
                count = int(expr)
            except ValueError:
                msg = f"❌ 无效的骰子数量: {expr}"
                self.reply(msg)
                return
        else:
            count = 1  # 默认掷1个

        if count <= 0:
            msg = "❌ 骰子数量必须大于0"
            self.reply(msg)
            return

        if count > 20:  # 限制最大骰子数量
            count = 20
            msg = "⚠️ 骰子数量过多，已限制为20个"
            self.reply(msg)

        # 掷特殊骰子
        faces = self.config[self.owner_id]["special_dice"][user_id]
        results = []
        for _ in range(count):
            roll = random.choice(faces)
            results.append(roll)

        total = sum(results)
        user_name = get_user_name(self.robot, self.event.user_id)
        if count > 1:
            msg = f"🎲 {user_name} 特殊骰子掷出: {results} -> 总和: {total}"
        else:
            msg = f"🎲 {user_name} 特殊骰子掷出: {results[0]}"

        # 记录日志
        self.add_log("roll_special_dice", {
            "count": count,
            "results": results,
            "total": total
        })

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.ri(\+?-?\d+)?$"))
    def initiative(self):
        """先攻"""
        modifier = 0
        expr = self.event.msg[2:]  # 去掉 "ri"

        if expr:
            try:
                modifier = int(expr)
            except ValueError:
                msg = "❌ 无效的先攻修正值"
                self.reply(msg)
                return

        roll = random.randint(1, 20)
        total = roll + modifier

        # 记录到战斗系统中
        battle = self.config[self.owner_id]["battles"].get("current")
        if battle:
            user_id = self.event.user_id
            user_name = get_user_name(self.robot, user_id)
            battle["initiatives"][user_id] = {
                "name": user_name,
                "roll": total,
                "modifier": modifier,
                "acted": False  # 标记是否已行动
            }
            self.save_config()

        user_name = get_user_name(self.robot, self.event.user_id)
        mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
        msg = f"⚔️ {user_name} 先攻: {roll}{mod_str} = {total}"

        # 记录日志
        self.add_log("initiative", {
            "roll": roll,
            "modifier": modifier,
            "total": total
        })

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.init$"))
    def show_initiative(self):
        """显示先攻列表"""
        battle = self.config[self.owner_id]["battles"].get("current")
        if not battle or not battle.get("initiatives"):
            msg = "当前没有进行中的战斗或无人掷先攻"
        else:
            initiatives = battle["initiatives"]
            sorted_init = sorted(initiatives.items(), key=lambda x: x[1]["roll"], reverse=True)
            msg = "⚔️ 先攻列表:\n"
            for i, (user_id, data) in enumerate(sorted_init, 1):
                status = "✅" if data.get("acted", False) else "⏳"
                mod_str = f"+{data['modifier']}" if data['modifier'] >= 0 else str(data['modifier'])
                msg += f"{i}. {status} {data['name']}: {data['roll']} (调整值: {mod_str})\n"

            # 显示当前回合信息
            if battle.get("current_round", 0) > 0:
                current_turn = battle.get("current_turn", 0)
                if current_turn < len(sorted_init):
                    current_player = sorted_init[current_turn][1]["name"]
                    msg += f"\n🔄 第{battle['current_round']}回合 - 当前行动: {current_player}"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.hp([+-]\d+)$"))
    def hp_change(self):
        """HP 管理"""
        try:
            change = int(self.match(r"^hp([+-]\d+)$").group(1))
            pc = self.get_user_pc()
            hp = pc.get("HP", 10)
            new_hp = max(0, hp + change)
            pc["HP"] = new_hp
            self.save_user_pc(pc)

            user_name = get_user_name(self.robot, self.event.user_id)
            change_str = f"+{change}" if change >= 0 else str(change)
            msg = f"❤️ {user_name} HP: {hp} {change_str} = {new_hp}"

            # 记录日志
            self.add_log("hp_change", {
                "change": change,
                "old_hp": hp,
                "new_hp": new_hp
            })

        except ValueError:
            msg = "❌ HP变化值必须是数字"
        except Exception as e:
            msg = f"HP修改错误: {e}"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.mp([+-]\d+)$"))
    def mp_change(self):
        """MP 管理"""
        try:
            change = int(self.event.msg[3:])  # 去掉 ".mp"
            pc = self.get_user_pc()
            mp = pc.get("MP", 10)
            new_mp = max(0, mp + change)
            pc["MP"] = new_mp
            self.save_user_pc(pc)

            user_name = get_user_name(self.robot, self.event.user_id)
            change_str = f"+{change}" if change >= 0 else str(change)
            msg = f"💙 {user_name} MP: {mp} {change_str} = {new_mp}"

            # 记录日志
            self.add_log("mp_change", {
                "change": change,
                "old_mp": mp,
                "new_mp": new_mp
            })

        except ValueError:
            msg = "❌ MP变化值必须是数字"
        except Exception as e:
            msg = f"MP修改错误: {e}"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.pc\s.*$"))
    def pc_manage(self):
        """人物卡管理"""
        msg = ""

        if self.match(r"^\.pc new\s?(\S+)?"):
            name = self.match(r"^\.pc new\s?(\S+)?").group(1) or "无名氏"
            pc = {"Name": name, "HP": 10, "MP": 10, "力量": 50, "体质": 50, "敏捷": 50, "理智": 50, "SAN": 50}
            self.save_user_pc(pc)
            user_name = get_user_name(self.robot, self.event.user_id)
            msg = f"🧾 {user_name} 新建人物卡: {name}, HP={pc['HP']}, MP={pc['MP']}"
        elif self.match(r"^\.pc auto$"):
            pc = self.generate_coc_character()
            self.save_user_pc(pc)
            user_name = get_user_name(self.robot, self.event.user_id)
            msg = f"🎲 {user_name} 自动生成人物卡: {pc['Name']}\n"
            msg += f"力量{pc.get('STR', 50)} 体质{pc.get('CON', 50)} 体型{pc.get('SIZ', 50)}\n"
            msg += f"敏捷{pc.get('DEX', 50)} 外貌{pc.get('APP', 50)} 智力{pc.get('INT', 50)}\n"
            msg += f"意志{pc.get('POW', 50)} 教育{pc.get('EDU', 50)} 幸运{pc.get('幸运', 50)}\n"
            msg += f"HP: {pc.get('HP', 10)} MP: {pc.get('MP', 10)} SAN: {pc.get('SAN', 50)}"
        elif self.match(r"^\.pc set\s?(\S+)=(-?\d+)$"):
            key, value = self.match(r"^\.pc set\s?(\S+)=(-?\d+)$").groups()
            pc = self.get_user_pc()
            pc[key] = int(value)
            self.save_user_pc(pc)
            user_name = get_user_name(self.robot, self.event.user_id)
            msg = f"📝 {user_name} 设置 {key} = {value}"
        elif self.match(r"^\.pc show$"):
            pc = self.get_user_pc()
            if pc:
                user_name = get_user_name(self.robot, self.event.user_id)
                msg = self.format_character_sheet(pc, user_name)
            else:
                msg = "尚未建立人物卡"
        elif self.match(r"^\.pc show\s+@?(\d+)$"):
            target_id = self.match(r"^\.pc show\s+@?(\d+)$").group(1)
            pc = self.get_user_pc(target_id)
            if pc:
                user_name = get_user_name(self.robot, target_id)
                msg = self.format_character_sheet(pc, user_name)
            else:
                user_name = get_user_name(self.robot, target_id)
                msg = f"{user_name} 尚未建立人物卡"
        elif self.match(r"^\.pc del$"):
            db_path = self.get_data_path(self.config["database"])
            conn = sqlite3.connect(db_path)
            self.init_rpg_db(conn)
            cur = conn.cursor()

            cur.execute(
                "DELETE FROM characters WHERE owner_id=? AND user_id=?",
                (self.owner_id, str(self.event.user_id))
            )
            conn.commit()
            conn.close()

            user_name = get_user_name(self.robot, self.event.user_id)
            msg = f"🗑️ {user_name} 已删除人物卡"

            # 记录日志
            self.add_log("delete_pc", {})
        else:
            msg = "pc 指令用法: new/auto/set/show/del"

        self.reply(msg)

    def format_character_sheet(self, pc, user_name):
        """格式化人物卡显示"""
        msg = f"📜 {user_name} 的人物卡信息:\n"

        # 基本信息
        if "Name" in pc:
            msg += f"名称: {pc['Name']}\n"

        # 主要属性
        main_attrs = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU", "幸运"]
        main_values = []
        for attr in main_attrs:
            if attr in pc:
                main_values.append(f"{attr}:{pc[attr]}")
        if main_values:
            msg += "主要属性: " + " ".join(main_values) + "\n"

        # 状态属性
        status_attrs = ["HP", "MP", "SAN", "理智"]
        status_values = []
        for attr in status_attrs:
            if attr in pc:
                status_values.append(f"{attr}:{pc[attr]}")
        if status_values:
            msg += "状态: " + " ".join(status_values) + "\n"

        # 技能（分组显示）
        skill_categories = {}
        for category, skills in self.COC_SKILLS.items():
            for skill in skills:
                if skill in pc:
                    if category not in skill_categories:
                        skill_categories[category] = []
                    skill_categories[category].append(f"{skill}:{pc[skill]}")

        for category, skills in skill_categories.items():
            msg += f"\n{category}:\n"
            msg += " ".join(skills) + "\n"

        # 其他技能
        other_skills = []
        for skill, value in pc.items():
            if (skill not in main_attrs and skill not in status_attrs and 
                skill != "Name" and not any(skill in cat_skills for cat_skills in self.COC_SKILLS.values())):
                other_skills.append(f"{skill}:{value}")

        if other_skills:
            msg += f"\n其他技能:\n"
            msg += " ".join(other_skills)

        return msg

    @via(lambda self: self.au(2) and self.match(r"^\.team\s.*$"))
    def team_manage(self):
        """队伍管理"""
        msg = ""

        if self.match(r"^\.team create\s+(\S+)$"):
            team_name = self.match(r"^\.team create\s+(\S+)$").group(1)
            user_id = self.event.user_id
            user_name = get_user_name(self.robot, user_id)

            # 检查是否已在其他队伍
            for tname, team in self.config[self.owner_id]["teams"].items():
                if str(user_id) in team["members"]:
                    msg = f"❌ 您已在 {tname} 队伍中，请先退出再加入新队伍"
                    self.reply(msg)
                    return

            self.config[self.owner_id]["teams"][team_name] = {
                "leader": user_id,
                "members": {str(user_id): user_name},
                "created": datetime.datetime.now().isoformat()
            }
            self.save_config()
            msg = f"👥 队伍 {team_name} 创建成功，您是队长"

            # 记录日志
            self.add_log("team_create", {"team_name": team_name})

        elif self.match(r"^\.team join\s+(\S+)$"):
            team_name = self.match(r"^\.team join\s+(\S+)$").group(1)
            if team_name not in self.config[self.owner_id]["teams"]:
                msg = f"❌ 队伍 {team_name} 不存在"
            else:
                user_id = self.event.user_id
                user_name = get_user_name(self.robot, user_id)

                # 检查是否已在其他队伍
                for tname, team in self.config[self.owner_id]["teams"].items():
                    if str(user_id) in team["members"] and tname != team_name:
                        msg = f"❌ 您已在 {tname} 队伍中，请先退出再加入新队伍"
                        self.reply(msg)
                        return

                self.config[self.owner_id]["teams"][team_name]["members"][str(user_id)] = user_name
                self.save_config()
                msg = f"👥 {user_name} 加入了队伍 {team_name}"
    
                # 记录日志
                self.add_log("team_join", {"team_name": team_name})
    
        elif self.match(r"^\.team leave$"):
            user_id = self.event.user_id
            user_name = get_user_name(self.robot, user_id)

            # 查找用户所在的队伍
            found = False
            for team_name, team in self.config[self.owner_id]["teams"].items():
                if str(user_id) in team["members"]:
                    # 如果是队长，解散队伍
                    if team["leader"] == user_id:
                        del self.config[self.owner_id]["teams"][team_name]
                        msg = f"👥 队长 {user_name} 离开了队伍，队伍 {team_name} 已解散"
                    else:
                        del self.config[self.owner_id]["teams"][team_name]["members"][str(user_id)]
                        msg = f"👥 {user_name} 离开了队伍 {team_name}"
                    found = True
                    break

            if not found:
                msg = "❌ 您不在任何队伍中"
            self.save_config()

            # 记录日志
            if found:
                self.add_log("team_leave", {"team_name": team_name})
    
        elif self.match(r"^\.team info$"):
            user_id = self.event.user_id

            # 查找用户所在的队伍
            found = False
            for team_name, team in self.config[self.owner_id]["teams"].items():
                if str(user_id) in team["members"]:
                    leader_name = get_user_name(self.robot, team["leader"])
                    members = ", ".join(team["members"].values())
                    created_date = datetime.datetime.fromisoformat(team["created"]).strftime("%Y-%m-%d %H:%M")
                    msg = f"👥 队伍 {team_name} 信息:\n创建时间: {created_date}\n队长: {leader_name}\n成员: {members}"
                    found = True
                    break

            if not found:
                msg = "❌ 您不在任何队伍中"
        elif self.match(r"^\.team list$"):
            teams = self.config[self.owner_id]["teams"]
            if not teams:
                msg = "当前没有队伍"
            else:
                msg = "👥 所有队伍:\n"
                for team_name, team in teams.items():
                    leader_name = get_user_name(self.robot, team["leader"])
                    member_count = len(team["members"])
                    created_date = datetime.datetime.fromisoformat(team["created"]).strftime("%m-%d")
                    msg += f"{team_name} (队长: {leader_name}, 成员: {member_count}人, 创建: {created_date})\n"
        else:
            msg = "team 指令用法: create/join/leave/info/list"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.battle\s.*$"))
    def battle_manage(self):
        """战斗管理"""
        msg = ""

        if self.match(r"^\.battle start$"):
            user_id = self.event.user_id

            # 检查用户是否在队伍中
            user_team = None
            for team_name, team in self.config[self.owner_id]["teams"].items():
                if str(user_id) in team["members"]:
                    user_team = team_name
                    break

            if not user_team:
                msg = "❌ 您不在任何队伍中，无法开始战斗"
            else:
                team = self.config[self.owner_id]["teams"][user_team]
                if team["leader"] != user_id:
                    msg = "❌ 只有队长可以开始战斗"
                else:
                    self.config[self.owner_id]["battles"]["current"] = {
                        "team": user_team,
                        "initiatives": {},
                        "round": 0,
                        "current_turn": 0,
                        "started": datetime.datetime.now().isoformat()
                    }
                    self.save_config()
                    msg = f"⚔️ 战斗开始！队伍 {user_team} 进入战斗状态，请队员使用 .ri 命令掷先攻"
        
                    # 记录日志
                    self.add_log("battle_start", {"team": user_team})
        
        elif self.match(r"^\.battle end$"):
            user_id = self.event.user_id

            if "current" not in self.config[self.owner_id]["battles"]:
                msg = "❌ 当前没有进行中的战斗"
            else:
                battle = self.config[self.owner_id]["battles"]["current"]
                team_name = battle["team"]

                # 检查是否是队长
                team = self.config[self.owner_id]["teams"][team_name]
                if team["leader"] != user_id:
                    msg = "❌ 只有队长可以结束战斗"
                else:
                    del self.config[self.owner_id]["battles"]["current"]
                    self.save_config()
                    msg = f"⚔️ 战斗结束！队伍 {team_name} 退出战斗状态"
        
                    # 记录日志
                    self.add_log("battle_end", {
                        "team": team_name,
                        "rounds": battle.get("round", 0)
                    })
        
        elif self.match(r"^\.battle status$"):
            if "current" not in self.config[self.owner_id]["battles"]:
                msg = "当前没有进行中的战斗"
            else:
                battle = self.config[self.owner_id]["battles"]["current"]
                team_name = battle["team"]
                round_num = battle["round"]
                initiative_count = len(battle["initiatives"])

                msg = f"⚔️ 战斗状态:\n队伍: {team_name}\n回合: {round_num}\n已掷先攻: {initiative_count}人"

                if battle["initiatives"]:
                    sorted_init = sorted(battle["initiatives"].items(), key=lambda x: x[1]["roll"], reverse=True)
                    msg += "\n先攻顺序:"
                    for i, (user_id, data) in enumerate(sorted_init, 1):
                        status = "✅" if data.get("acted", False) else "⏳"
                        msg += f"\n{i}. {status} {data['name']}: {data['roll']}"
            
                    # 显示当前回合信息
                    if round_num > 0:
                        current_turn = battle.get("current_turn", 0)
                        if current_turn < len(sorted_init):
                            current_player = sorted_init[current_turn][1]["name"]
                            msg += f"\n\n🔄 第{round_num}回合 - 当前行动: {current_player}"

        elif self.match(r"^\.battle next$"):
            if "current" not in self.config[self.owner_id]["battles"]:
                msg = "❌ 当前没有进行中的战斗"
            else:
                battle = self.config[self.owner_id]["battles"]["current"]
    
                if not battle["initiatives"]:
                    msg = "❌ 无人掷先攻，无法开始回合"
                else:
                    sorted_init = sorted(battle["initiatives"].items(), key=lambda x: x[1]["roll"], reverse=True)
                    current_turn = battle.get("current_turn", 0)
                    round_num = battle.get("round", 0)
        
                    if current_turn == 0 and round_num == 0:
                        # 开始第一回合
                        battle["round"] = 1
                        msg = f"🔄 第1回合开始！"
                    else:
                        # 标记当前玩家已行动
                        if current_turn < len(sorted_init):
                            user_id, data = sorted_init[current_turn]
                            battle["initiatives"][user_id]["acted"] = True
            
                        # 移动到下一个玩家
                        current_turn += 1
            
                        if current_turn >= len(sorted_init):
                            # 回合结束
                            current_turn = 0
                            battle["round"] += 1
                            # 重置所有玩家的行动状态
                            for user_id in battle["initiatives"]:
                                battle["initiatives"][user_id]["acted"] = False
                
                            msg = f"🔄 第{battle['round']}回合开始！"
                        else:
                            msg = f"⏭️ 轮到下一位玩家行动"
        
                    battle["current_turn"] = current_turn
                    self.save_config()
        
                    # 添加当前行动者信息
                    if current_turn < len(sorted_init):
                        current_player = sorted_init[current_turn][1]["name"]
                        msg += f"\n当前行动: {current_player}"
        else:
            msg = "battle 指令用法: start/end/status/next"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.jrrp$"))
    def jrrp(self):
        """今日人品"""
        # 基于用户ID和日期生成确定性的随机数
        today = datetime.date.today().isoformat()
        seed = int(f"{self.event.user_id}{today.replace('-', '')}")
        random.seed(seed)
        rp = random.randint(1, 100)
        random.seed()  # 重置随机种子

        # 根据人品值给出评价
        if rp >= 90:
            comment = "🎉 大吉大利！"
        elif rp >= 70:
            comment = "✨ 运气不错！"
        elif rp >= 50:
            comment = "👍 平平无奇"
        elif rp >= 30:
            comment = "😐 小心为上"
        else:
            comment = "⚠️ 诸事不宜"

        user_name = get_user_name(self.robot, self.event.user_id)
        msg = f"✨ {user_name} 今日人品值: {rp} {comment}"

        # 记录日志
        self.add_log("jrrp", {"value": rp})

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.(coin|掷硬币)$"))
    def coin(self):
        """掷硬币"""
        result = random.choice(["正面", "反面"])
        user_name = get_user_name(self.robot, self.event.user_id)
        msg = f"🪙 {user_name} 硬币结果: {result}"

        # 记录日志
        self.add_log("coin", {"result": result})

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.coc$"))
    def coc_help(self):
        """显示CoC相关帮助"""
        msg = "🐙 CoC 跑团帮助:\n"
        msg += "• 使用 .pc auto 自动生成符合规则的角色卡\n"
        msg += "• 使用 .stlist 查看标准技能列表\n"
        msg += "• 理智检定(.sc)会在损失大量SAN或大失败时触发疯狂症状\n"
        msg += "• 战斗中使用 .battle next 推进回合\n"
        msg += "• 使用 .log 查看最近的骰子记录"

        self.reply(msg)

    @via(lambda self: self.au(2) and self.match(r"^\.log$"))
    def show_log(self):
        """显示最近的日志"""
        logs = self.config[self.owner_id].get("logs", [])
        if not logs:
            msg = "暂无日志记录"
        else:
            msg = "📋 最近活动记录:\n"
            for log in logs[-10:]:  # 显示最近10条记录
                timestamp = datetime.datetime.fromisoformat(log["timestamp"]).strftime("%H:%M")
                user_name = get_user_name(self.robot, log["user_id"])
                msg += f"{timestamp} {user_name}: {log['action']}\n"

        self.reply(msg)