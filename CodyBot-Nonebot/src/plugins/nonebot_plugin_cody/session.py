#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: session
# Created on: 2023/1/31

import asyncio
import threading
import time
from transformers import GPT2TokenizerFast
from nonebot import get_bot
from nonebot.adapters.mirai2 import MessageEvent, FriendMessage, MessageSegment, GroupMessage, TempMessage, Bot
from .config import *
from .presets import BUILTIN_PRIVATE_PRESET, BUILTIN_GROUP_PRESET, BUILTIN_PRIVATE_NSFW_PRESET
from .openai import get_chat_response, CODY_HEADER, ANONYMOUS_HUMAN_HEADER

CREATOR_ID = 2226997440
CREATOR_GF_ID = 2739097870

TOKENIZER = GPT2TokenizerFast.from_pretrained("gpt2")
API_INDEX = -1
INVALID_APIs = []
PUNCTUATION_SETS = {"。", "！", "？", ".", "!", "?", ";", "；", "……", "~", "~"}


class Session:
    def __init__(self, id, is_group=False, name=None):
        self.live = True
        self.is_group = is_group
        self.session_id = id
        self.user_id = id
        self.time_format_text = "%Y-%m-%d %H:%M:%S %A"
        if is_group:
            self.static_preset = BUILTIN_GROUP_PRESET
            self.name = "people"
        else:
            if id == CREATOR_ID:
                name = "Icy"
            elif id == CREATOR_GF_ID:
                name = "Miuto"
            else:
                if name is not None:
                    upper = name.upper()
                    if "ICY" in upper:
                        name = name.upper().replace("ICY", "FakeTheBuster")
                    if "CCY" in upper:
                        name = name.upper().replace("CCY", "FakeTheBuster")
                    if "吸吸歪" in upper:
                        name = name.upper().replace("吸吸歪", "FakeTheBuster")
                    if "MIUTO" in upper:
                        name = name.upper().replace("MIUTO", "FakeTheBuster")
            self.name = name
            self.static_preset = BUILTIN_PRIVATE_PRESET.format(name)

        # 可部分储存部分
        self.addons = [ele(self) for ele in REGISTERED_ADDONS]  # 插件
        self.registered_alarms = {}  # 注册的alarm，格式：{uid: [timestamp, async_callback_method, param]}

        # 可储存部分
        self.conversation = []  # 对话缓存
        self.conversation_ts = []  # 对话时间戳缓存
        self.statics_conversation_mad_span_tokens = []  # mad span内对话所耗tokens缓存
        self.statics_conversation_mad_span_ts = []  # mad span内对话时间戳缓存
        self.users = {}  # 用户名称缓存
        self.mad_status_change_ts = 0  # mad时间戳
        self.mad_level = 0  # mad等级
        self.msg_count = 0  # mad消息相对数量

        # 配置部分
        self.max_session_tokens = CODY_CONFIG.cody_max_session_tokens

        threading.Thread(target=self.alarm_trigger_thread).start()
        logger.info("[session {}] sub thread started".format(self.session_id))

    # 重置会话
    def reset(self):
        self.users = {}
        self.conversation = []
        self.conversation_ts = []
        self.statics_conversation_mad_span_tokens = []
        self.statics_conversation_mad_span_ts = []
        self.mad_status_change_ts = 0
        self.mad_level = 0
        self.msg_count = 0

    def kill(self):
        self.live = False

    def alarm_trigger_thread(self):
        cnt = 0
        while self.live:
            if cnt >= 10:
                try:
                    cnt = 0
                    ts_now = time.time()
                    triggered_alarms = []
                    for ele in self.registered_alarms.keys():
                        if ts_now > self.registered_alarms[ele][0]:
                            logger.debug("[session {}] alarm triggered of ID {}".format(self.session_id, ele))
                            async_object = self.registered_alarms[ele][1](*self.registered_alarms[ele][2])
                            asyncio.run(async_object)
                            triggered_alarms.append(ele)

                    for ele in triggered_alarms:
                        self.registered_alarms.pop(ele)
                except Exception as err:
                    logger.error(f"[session {self.session_id}] error while executing alarm, {err}")
            else:
                cnt += 1
                time.sleep(0.1)

    # 设置人格
    def set_preset(self, msg: str):
        self.static_preset = msg
        self.reset()

    def generate_preset_with_addons(self, preset):
        for ele in self.addons:
            preset = ele(preset)
        return preset

    # 导入用户会话
    async def load_user_session(self):
        pass

    # 导出用户会话
    def dump_user_session(self):
        logger.debug("dump session")
        return self.static_preset + ANONYMOUS_HUMAN_HEADER + ''.join(self.conversation)

    def generate_time_header_for_chat(self, addon_text=None):
        if addon_text is not None:
            time_header = "\n[{}. {}]".format(
                time.strftime(self.time_format_text),
                addon_text
            )
        else:
            time_header = "\n[{}]".format(
                time.strftime(self.time_format_text)
            )
        return time_header

    def generate_status_text_for_chat(self):
        status_header = "\n"
        for ele in self.addons:
            status_header = ele.update_status_callback(status_header)
        return status_header

    def check_and_forget_conversations(self):
        if len(self.conversation):
            # 检查时间
            ts = self.conversation_ts[0]
            while time.time() - ts > CODY_CONFIG.cody_session_forget_timeout:
                logger.debug(
                    f"最早的会话超过 {CODY_CONFIG.cody_session_forget_timeout} 秒，"
                    f"删除最早的一次会话，执行忘记")
                del self.conversation[0]
                del self.conversation_ts[0]
                if len(self.conversation_ts):
                    ts = self.conversation_ts[0]
                else:
                    break

    def generate_prompts(self, preset, status_header, time_header, human_header, msg) -> (int, str):
        prompt = preset + status_header + "\n" + ''.join(self.conversation) + time_header + human_header + msg

        token_len = len(TOKENIZER.encode(prompt))
        logger.debug("[session {}] Using token: {}".format(self.session_id, token_len))

        # 检查长度
        while token_len > self.max_session_tokens - CODY_CONFIG.cody_gpt3_max_tokens:
            logger.debug(
                f"[session {self.session_id}] "
                f"长度超过 {self.max_session_tokens} - max_token"
                f" = {self.max_session_tokens - CODY_CONFIG.cody_gpt3_max_tokens}，"
                f"删除最早的一次会话")
            del self.conversation[0]
            del self.conversation_ts[0]
            prompt = preset + "\n" + status_header + "\n" + \
                     ''.join(self.conversation) + time_header + human_header + msg
            token_len = len(TOKENIZER.encode(prompt))

        return token_len, prompt

    async def generate_GPT3_feedback(self, prompt, teller_name, conversation_header: str) -> (bool, str, str):
        global API_INDEX
        # 一个api失效时尝试下一个
        status = False
        # 警告字段（不会加入记忆）
        warning_text = ""

        for i in range(len(APIKEY_LIST)):
            API_INDEX = (API_INDEX + 1) % len(APIKEY_LIST)
            logger.debug(f"使用 API: {API_INDEX + 1}")
            logger.debug("Full Text: {}".format(prompt))
            res, status = await asyncio.get_event_loop().run_in_executor(None, get_chat_response,
                                                                         APIKEY_LIST[API_INDEX],
                                                                         prompt, teller_name)
            if len(INVALID_APIs):
                valid_api_count = len(APIKEY_LIST) - len(INVALID_APIs)
                logger.warning("当前有效API数量: {}/{}".format(valid_api_count, len(APIKEY_LIST)))
                if valid_api_count <= 1 and status:
                    warning_text = f" [警告：仅剩1个API密钥能够正常工作]"

            if status:
                if API_INDEX + 1 in INVALID_APIs:
                    INVALID_APIs.remove(API_INDEX + 1)
                break
            else:
                logger.error(f"API: {APIKEY_LIST[API_INDEX]}(ID: {API_INDEX + 1}) 出现错误")
                if API_INDEX + 1 not in INVALID_APIs:
                    INVALID_APIs.append(API_INDEX + 1)

        if status:
            if not res.replace(" ", ""):
                res = "……"
            logger.debug("AI 返回：{}".format(res))
            self.conversation.append(f"{conversation_header}{res}")
            self.conversation_ts.append(time.time())
            logger.debug("当前对话（ID:{}）: {}".format(self.session_id, self.conversation))
            for addon in self.addons:
                res = addon.update_response_callback(res)
        else:
            # 超出长度或者错误自动重置
            self.reset()

        return status, res, warning_text

    # 会话
    async def get_chat_response(self, msg, user_id: int = None, user_name: str = None) -> str:
        global INVALID_APIs
        if user_id is not None or user_name is not None:
            if user_id == CREATOR_ID:
                user_name = "Icy"
            elif user_id == CREATOR_GF_ID:
                user_name = "Miuto"
            elif user_name is not None:
                upper = user_name.upper()
                if "ICY" in upper:
                    user_name = user_name.upper().replace("ICY", "FakeTheBuster")
                if "CCY" in upper:
                    user_name = user_name.upper().replace("CCY", "FakeTheBuster")
                if "吸吸歪" in upper:
                    user_name = user_name.upper().replace("吸吸歪", "FakeTheBuster")
                if "MIUTO" in upper:
                    user_name = user_name.upper().replace("MIUTO", "FakeTheBuster")
            if user_name is None:
                if user_id not in self.users:
                    self.users.update({user_id: len(self.users)})
                user_session_id = self.users[user_id]
                human_header = "\nHuman_{}:".format(user_session_id)
            else:
                human_header = "\n{}:".format(user_name)
        else:
            human_header = ANONYMOUS_HUMAN_HEADER

        logger.debug("处理消息，发送人头部：{}".format(human_header))

        if msg[-1] not in PUNCTUATION_SETS:
            msg += "。"

        # 初始态预设
        preset = self.static_preset
        # 预设加载补丁
        preset = self.generate_preset_with_addons(preset)
        # 生成时间头
        time_header = self.generate_time_header_for_chat()
        # 生成状态头
        status_header = self.generate_status_text_for_chat()
        # 检查时间
        self.check_and_forget_conversations()
        # 生成提示词
        token_len, prompt = self.generate_prompts(preset, status_header, time_header, human_header, msg)
        # 获得反馈
        status, res, warning_text = await self.generate_GPT3_feedback(prompt, human_header[1:-1],
                                                                      f"{time_header}{human_header}{msg}{CODY_HEADER}")

        return res + warning_text


class BaseAddonManager:

    def __init__(self, session: Session,
                 addon_msg: str,
                 name_format_count: int = 2,
                 priority: int = 10):
        self.session = session
        self.preset_base: str = addon_msg
        self.subject_name: str = self.session.name
        self.name_format_count = name_format_count
        self.priority = priority

    def __str__(self):
        return self.preset_base.format(*[self.subject_name for i in range(self.name_format_count)])

    def __call__(self, base_preset: str) -> str:
        ret = base_preset
        addon = str(self)
        if (not base_preset or base_preset[-1] != " ") and (not addon or addon[-1] != " "):
            ret += " "

        return ret + addon

    def set_subjects(self, subject_name):
        self.subject_name = subject_name

    def update_status_callback(self, status_text: str) -> str:
        return status_text

    def update_response_callback(self, resp: str) -> str:
        return resp

    def update_input_callback(self, input: str) -> str:
        return input


class CommandAddon(BaseAddonManager):

    def __init__(self, session_class):
        addon_text = "An programmatic command is a text which must be placed separately in parentheses after Cody's " \
                     "reply. Multiple actions can be placed at the same time separately. programmatic command " \
                     "formatted text should always uses half-width characters and no space between parameters. Cody " \
                     "will never try to ask others to use programmatic command or even talk about it. programmatic " \
                     "command text can only be added to reply in condition of below. Never quoting an programmatic " \
                     "command or its usage."

        if session_class.is_group:
            super().__init__(session_class, "", name_format_count=0, priority=2)
        else:
            super().__init__(session_class, addon_text, name_format_count=0, priority=2)


class ReminderAddon(BaseAddonManager):

    def __init__(self, session_class):
        addon_text = "Cody will remember a schedule when {} said, and never remember a schedule that has existed in " \
                     "Cody's memory. Cody can only use " \
                     "programmatic command formatted like \"(SC|<ADD/EDIT/REMOVE>|<unique integer schedule " \
                     "number>|<time of " \
                     "schedule>|<full description of event without subject>^#)\" to remember, edit or remove a " \
                     "schedule, time format " \
                     "like %Y-%m-%d %H:%M:%S. Conversation sample: " \
                     "\"Human:晚上好。;Cody:晚上好呀。;Human:我明天早上9点有个会，帮我记一下。;Cody:好的，已经记下啦。 (SC|ADD|1|2019-08-20 " \
                     "9:00:00|attend a meeting^#)\". Cody will always use plain " \
                     "text when quoting instead of programmatic command format. Never use programmatic command format " \
                     "when " \
                     "retelling or quoting. "

        if session_class.is_group:
            super().__init__(session_class, "", name_format_count=0, priority=2)
        else:
            super().__init__(session_class, addon_text, name_format_count=3, priority=2)

        self.reminders = {}
        self.alarm_id_header = "cody_reminder"

    def update_status_callback(self, status_text: str) -> str:
        if not self.session.is_group:
            reminder_sequence = ""
            reminder_ids = list(self.reminders.keys())
            reminder_ids.sort()
            if not len(reminder_ids):
                reminder_sequence = "None"
            else:
                for id in reminder_ids:
                    content = self.reminders[id]
                    alarm_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(content['alarm']))
                    reminder_sequence += f"ID:{id},Deadline:{alarm_time},Event:{content['text']}; "

            status_text += "\n"
            status_text += "(All schedules for {} in Cody's memory, and Cody will never use programmatic command " \
                           "to remember these again: {})".format(self.session.name, reminder_sequence)

        return status_text

    async def action_retell(self, reminder_id: int):
        reminder = self.reminders[reminder_id]
        preset = self.session.static_preset
        preset = self.session.generate_preset_with_addons(preset)
        status_header = self.session.generate_status_text_for_chat()
        alarm_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reminder['alarm']))
        mixed_time_header = self.session.generate_time_header_for_chat(
            "Cody need to remind {} gently in plain text for schedule with ID:{},Time:{},Event:{}. And Cody will no "
            "longer need to remember this schedule.".format(
                self.session.name, reminder_id, alarm_time, reminder['text'])
        )

        self.session.check_and_forget_conversations()

        token_len, prompt = self.session.generate_prompts(preset, status_header, mixed_time_header, CODY_HEADER, '')

        status, res, warning_text = await self.session.generate_GPT3_feedback(
            prompt, self.session.name, f"{mixed_time_header}{CODY_HEADER}")

        if status:
            feedback = res
            self.reminders.pop(reminder_id)
        else:
            feedback = "[Cody正尝试提醒您的一个计划日程，但出于某种原因失败了]"

        event = FriendMessage.parse_obj(
            {
                'self_id': 0,
                'type': 0,
                'messageChain': '',
                'sender': {
                    'id': self.session.session_id,
                    'nickname': self.session.name,
                    'remark': self.session.name
                }
            }
        )

        await get_bot().send(event, feedback)

    def update_response_callback(self, resp: str) -> str:

        if self.session.is_group:
            return resp

        def convert_time(time_str) -> int:
            timeArray = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            ts = int(time.mktime(timeArray))
            return ts

        add_count = 0
        edit_count = 0
        remove_count = 0
        failure_count = 0

        while True:
            start_ost = resp.find("SC|")
            if start_ost != -1:
                end_ost = resp[start_ost:].find("^#") + start_ost + 2
                cmd_text = resp[start_ost:end_ost]
                logger.debug("Reminder Command Detected: {}".format(cmd_text))

                try:
                    cmd = cmd_text[:-2].split("|")
                    action = cmd[1].upper()
                    reminder_id = int(cmd[2])

                    if "ADD" in action:
                        reminder_ts = convert_time(cmd[3])
                        self.reminders.update({reminder_id: {"alarm": reminder_ts,
                                                             "text": cmd[4]}})
                        add_count += 1
                        self.session.registered_alarms.update(
                            {
                                f"{self.alarm_id_header}_{reminder_id}": [
                                    reminder_ts,  # 定时任务时间戳
                                    self.action_retell,  # 定时任务回调函数
                                    (reminder_id,)  # 定时任务回调函数参数
                                ]
                            }
                        )

                    elif "EDIT" in action:
                        reminder_ts = convert_time(cmd[3])
                        self.reminders.update({reminder_id: {"alarm": reminder_ts,
                                                             "text": cmd[4]}})
                        edit_count += 1
                        self.session.registered_alarms.update(
                            {
                                f"{self.alarm_id_header}_{reminder_id}": [
                                    reminder_ts,  # 定时任务时间戳
                                    self.action_retell,  # 定时任务回调函数
                                    (reminder_id,)  # 定时任务回调函数参数
                                ]
                            }
                        )

                    elif "REMOVE" in action:
                        self.reminders.pop(reminder_id)
                        remove_count += 1
                        self.session.registered_alarms.pop(
                            f"{self.alarm_id_header}_{reminder_id}"
                        )

                    resp_f = resp[:start_ost]
                    if resp_f[-1] in ("(", "（"):
                        resp_f = resp_f[:-1]
                    resp_b = resp[end_ost:]
                    if resp_b[0] in (")", "）"):
                        resp_b = resp_b[1:]

                    resp = resp_f + resp_b
                except Exception as err:
                    logger.error("Failed when processing reminder command, {}".format(err))
                    failure_count += 1
                    break
            else:
                break

        if add_count:
            resp += " [添加了{}项日程]".format(add_count)
        if edit_count:
            resp += " [编辑了{}项日程]".format(edit_count)
        if remove_count:
            resp += " [移除了{}项日程]".format(remove_count)
        if failure_count:
            resp += " [{}个日程操作失败]".format(failure_count)

        return resp


REGISTERED_ADDONS = [CommandAddon, ReminderAddon]
# REGISTERED_ADDONS = []
