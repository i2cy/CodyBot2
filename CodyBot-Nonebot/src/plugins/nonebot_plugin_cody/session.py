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
from .config import *
from .presets import BUILTIN_PRIVATE_PRESET, BUILTIN_GROUP_PRESET
from .openai import get_chat_response, CODY_HEADER, ANONYMOUS_HUMAN_HEADER

CREATOR_ID = 2226997440
CREATOR_GF_ID = 2739097870

TOKENIZER = GPT2TokenizerFast.from_pretrained("gpt2")
API_INDEX = -1
INVALID_APIs = []
PUNCTUATION_SETS = {"。", "！", "？", ".", "!", "?", ";", "；", "……", "~", "~"}


class Session:
    def __init__(self, id, is_group=False, name=None, addons=None):
        self.live = True
        self.is_group = is_group
        self.session_id = id
        self.user_id = id
        self.time_format_text = "%Y-%m-%d %H:%M:%S %A"
        if addons is None:
            addons = []
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
        self.addons = [ele(self) for ele in addons]  # 插件
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
