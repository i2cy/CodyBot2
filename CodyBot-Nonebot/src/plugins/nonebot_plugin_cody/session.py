#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: session
# Created on: 2023/1/31

import asyncio
import base64
import threading
import time
from hashlib import sha256
from nonebot.adapters.onebot import V12Bot as Bot
from .config import *
from .builtin_basic_presets import BUILTIN_PRIVATE_PRESET, BUILTIN_GROUP_PRESET
from .api import get_chat_response, CODY_HEADER, ANONYMOUS_HUMAN_HEADER
from .userdata import Impression, ImpressionFrame
from .memory import Memory

CREATOR_ID = "80b3456f5f8398d38d659e2d2930e26544a61f0482180d00161cae78171d8d60"
CREATOR_GF_ID = "fa06dac2564d6b1995467e83c31e270b69de53160ce4c26ca913e28ea3a8669a"

API_INDEX = -1
INVALID_APIs = []
PUNCTUATION_SETS = {"。", "！", "？", ".", "!", "?", ";", "；", "……", "~", "~"}

# TODO: 移除旧版本GPT3的会话对象
class SessionGPT3:
    def __init__(self, id, is_group=False, username=None, addons=None):
        """
        Session class of chat with GPT-3 API

        :param id: int, session ID, which is the group ID when group chatting and private user ID when in private
        :param is_group: bool, weather if this session is a group chat session
        :param username: str, name of user or 'people' when in group chat
        :param addons: List(Addon), list of Addon class which should be a BaseAddonManager class
        """

        # status variables
        self.live = True

        # attributes
        self.is_group = is_group
        self.session_id = id
        self.user_id = id
        self.time_format_text = "%Y-%m-%d %H:%M:%S %A"

        # addon pre-initialize
        if addons is None:
            addons = []

        # initialize preset and username when in group chat
        if is_group:
            self.static_preset = BUILTIN_GROUP_PRESET
            self.name = "people"

        # initialize preset and username when in private chat
        else:
            id_sha256 = sha256(str(id).encode()).hexdigest()
            if id_sha256 == CREATOR_ID:  # creator detection
                username = "Icy"
            elif id_sha256 == CREATOR_GF_ID:  # creator's GF detection
                username = "Miuto"
            else:
                if username is not None:  # in case someone fake as an administrator

                    # prepare context
                    upper = username.upper()
                    upper = upper.replace(".", "")
                    upper = upper.replace(" ", "")

                    # name recognition
                    if "ICY" in upper:
                        username = username.upper().replace("ICY", "FakeTheBuster")
                    if "CCY" in upper:
                        username = username.upper().replace("CCY", "FakeTheBuster")
                    if "吸吸歪" in upper:
                        username = username.upper().replace("吸吸歪", "FakeTheBuster")
                    if "MIUTO" in upper:
                        username = username.upper().replace("MIUTO", "FakeTheBuster")

            # set username of session
            self.name = username
            self.static_preset = BUILTIN_PRIVATE_PRESET.format(username)

        # partially storage ables
        self.addons = [ele(self) for ele in addons]  # 插件
        self.registered_alarms = {}  # 注册的alarm，格式：{uid: [timestamp, async_callback_method, param]}

        # storage ables
        self.conversation = []  # 对话缓存
        self.conversation_ts = []  # 对话时间戳缓存
        self.users = {}  # 用户名称缓存

        # configuration reload
        self.max_session_tokens = CODY_CONFIG.cody_max_session_tokens

        # threading
        self.threads = []
        thread = threading.Thread(target=self.alarm_trigger_thread)
        self.threads.append(thread)

        # run threads
        [ele.start() for ele in self.threads]

    # 重置会话
    def reset(self):
        """
        reset current session including user's nickname, conversation short memory
        :return:
        """
        self.users = {}
        self.conversation = []
        self.conversation_ts = []

    def kill(self):
        """
        kill this session and all of its sub threads
        :return:
        """
        self.live = False
        [ele.join() for ele in self.threads]
        self.threads.clear()

    def alarm_trigger_thread(self):
        """
        timed event sub thread
        :return:
        """
        logger.info("[session {}] sub thread started".format(self.session_id))
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
        logger.info(f"[session {self.session_id}] alarm thread stopped")

    # 设置人格
    def set_preset(self, msg: str):
        """
        set current static preset with given string
        :param msg: str
        :return:
        """
        self.static_preset = msg
        self.reset()

    def generate_preset_with_addons(self, preset):
        """
        generate presets with addon fixing, make iteration of addons
        :param preset:
        :return:
        """
        for ele in self.addons:
            preset = ele(preset)
        return preset

    def generate_time_header_for_chat(self, addon_text=None):
        if addon_text is not None:
            time_header = "\n({}. {})".format(
                time.strftime(self.time_format_text),
                addon_text
            )
        else:
            time_header = "\n({})".format(
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

        token_len = len(prompt)
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
            token_len = len(prompt)

        return token_len, prompt

    async def get_GPT3_feedback(self, prompt, teller=None, stop_list=None, temperature=0.7,
                                frequency_p=0.0, presence_p=0.4):
        global API_INDEX, INVALID_APIs
        warning_text = ""
        res = ""
        status = False
        if stop_list is None:
            stop_list = []
        if teller is not None:
            stop_list.append("{}:".format(teller))
        for i in range(len(APIKEY_LIST)):
            API_INDEX = (API_INDEX + 1) % len(APIKEY_LIST)
            logger.debug(f"使用 API: {API_INDEX + 1}")
            logger.debug("Full Text: {}".format(prompt))
            res, status = await asyncio.get_event_loop().run_in_executor(None, get_chat_response,
                                                                         APIKEY_LIST[API_INDEX],
                                                                         prompt, stop_list,
                                                                         temperature, frequency_p,
                                                                         presence_p)
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

        return res, status, warning_text

    async def generate_GPT3_feedback(self, prompt, teller_name, conversation_header: str) -> (bool, str, str):
        res, status, warning_text = await self.get_GPT3_feedback(prompt, teller_name)

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
        if user_id is not None or user_name is not None:
            if user_id == CREATOR_ID:
                user_name = "Icy"
            elif user_id == CREATOR_GF_ID:
                user_name = "Miuto"
            elif user_name is not None:
                upper = user_name.upper()
                upper = upper.replace(" ", "")
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
                human_header = "\nHuman_{}: ".format(user_session_id)
            else:
                if user_id not in self.users:
                    if user_id == CREATOR_ID:
                        nickname = "Icy"
                    elif user_id == CREATOR_GF_ID:
                        nickname = "Miuto"
                    else:
                        # 生成昵称
                        prompt = "Convert following name into one friendly nickname in short that must with the same " \
                                 "language:\n{}\nreturn:".format(user_name)
                        nickname, status, wm = await self.get_GPT3_feedback(prompt, stop_list=["->", "\n"],
                                                                            temperature=0.0, frequency_p=0.2,
                                                                            presence_p=0.0)
                        # 检测昵称
                        if not status or nickname == "":
                            nickname = user_name
                            if nickname == "":
                                nickname = ANONYMOUS_HUMAN_HEADER
                    self.users.update({user_id: nickname})
                else:
                    nickname = self.users[user_id]
                human_header = "\n{}: ".format(nickname)
        else:
            human_header = ANONYMOUS_HUMAN_HEADER

        logger.debug("处理消息，发送人头部：{}".format(human_header))

        if msg[-1] not in PUNCTUATION_SETS:
            msg += "。"

        # 补丁输入回调处理
        for ele in self.addons:
            msg = ele.update_input_callback(msg)

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
        status, res, warning_text = await self.generate_GPT3_feedback(prompt, human_header[1:-2],
                                                                      f"{time_header}{human_header}{msg}{CODY_HEADER}")

        return res + warning_text


class SessionGPT35:
    def __init__(self, id: int, is_group: bool = False,
                 name: str = None, addons: list = None,
                 impression_db: Impression = None,
                 bot: Bot = None):
        """
        chat session of Cody using GPT-3.5
        :param id: int, usually QQ ID
        :param is_group: bool, weather the session is a group chat session
        :param name: str, default username or group name, will be overriden by impression data
        :param addons: list, list of addon objects with standard BaseAddon parent in addons.py
        :param impression_db: Impression, impression database interface
        :param bot: Bot, bot with onebot standard
        """
        # statics
        self.id = id
        self.is_group = is_group
        self.name = name
        self.addons = [obj(self) for obj in addons]  # initialize addon object with session object
        self.impression = impression_db
        self.bot: Bot = bot

        # threading
        self.live = True
        self.threads = []

        # storage ables

        # registered alarms, (format: [timestamp, string to execute])
        # executive must set ADDON_NAME of addon to call and ALARM_ARGS
        # of its alarm_callback method e.g.:
        #
        # # this is the test addons registered
        # class TestAddon(AddonBase):
        #     addon_name: str = "test_addon"
        #     def alarm_callback(group_id, message):
        #         self.session.bot.send_group_message(group_id, message)
        # # this is executive string example
        # """
        # ADDON_NAME = "test_addon"
        # ALARM_ARGS = (1222333444, "this is a test")
        # """
        self.registered_alarms = []

        # initialize a new conversation memory object
        self.conversation = Memory()
        # setup parents
        self.conversation.set_parent(self)
        # register logger
        self.conversation.set_logger(self.log)
        # register addons
        self.conversation.user_msg_post_proc = [func.user_msg_post_proc_callback for func in self.addons]
        self.conversation.cody_msg_post_proc = [func.cody_msg_post_proc_callback for func in self.addons]

    def log(self, message: str):
        """
        log information to system logger
        :param message: str
        :return:
        """
        label = "User"
        if self.is_group:
            label = "Group"

        logger.info(f"[{label}_{self.id}] {message}")

    def set_bot(self, bot: Bot):
        """
        set bot that capable with
        :param bot: Bot
        :return:
        """
        self.bot = bot

    def dump(self, use_base64: bool = True) -> str:
        """
        dump current session status to str
        :param use_base64: bool, use base64 to encode data
        :return: str
        """

        memory_json = self.conversation.to_json()
        save = {
            'conversations': memory_json,
            'alarms': self.registered_alarms
        }
        save = json.dumps(save)
        if use_base64:
            ret = (b'_B64' + base64.b64encode(save)).decode()
        else:
            ret = save

        return ret

    def load(self, status_str: str):
        """
        load current session status from previous saved status string
        :param status_str: str
        :return:
        """
        if len(status_str) > 4 and status_str[:4] == '_B64':
            status_str = status_str[4:]
            status_str = base64.b64decode(status_str).decode()

        status = json.loads(status_str)
        self.conversation.parse_obj(status['conversations'])
        self.registered_alarms = status['alarms']
        self.log(f"loaded {len(self.conversation.conversation)} conversations and {len(self.registered_alarms)} "
                 f"registered alarms from previously saved session")

    def alarm_trigger_thread(self):
        """
        timed event sub thread
        :return:
        """
        # TODO: 重新构建此定时事件处理线程循环

        logger.info("[session {}] sub thread started".format(self.session_id))
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
        logger.info(f"[session {self.session_id}] alarm thread stopped")

    def __del__(self):
        self.kill()

    def kill(self):
        """
        kill current session, which will make sub threads stop
        :return:
        """
        self.live = False
        [ele.join() for ele in self.threads]
        self.threads.clear()

    def reset(self):
        """
        reset current session and its memory, will not affect impression data
        :return:
        """
        # TODO: 完成会话reset方法

    async def get_chat_response(self, msg,
                                user_id: int = None,
                                user_name: str = None,
                                group_id: int = None) -> str:
        # TODO: 重新构建此GPT反馈获取函数

        if user_id is not None or user_name is not None:
            if user_id == CREATOR_ID:
                user_name = "Icy"
            elif user_id == CREATOR_GF_ID:
                user_name = "Miuto"
            elif user_name is not None:
                upper = user_name.upper()
                upper = upper.replace(" ", "")
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
                human_header = "\nHuman_{}: ".format(user_session_id)
            else:
                if user_id not in self.users:
                    if user_id == CREATOR_ID:
                        nickname = "Icy"
                    elif user_id == CREATOR_GF_ID:
                        nickname = "Miuto"
                    else:
                        # 生成昵称
                        prompt = "Convert following name into one friendly nickname in short that must with the same " \
                                 "language:\n{}\nreturn:".format(user_name)
                        nickname, status, wm = await self.get_GPT3_feedback(prompt, stop_list=["->", "\n"],
                                                                            temperature=0.0, frequency_p=0.2,
                                                                            presence_p=0.0)
                        # 检测昵称
                        if not status or nickname == "":
                            nickname = user_name
                            if nickname == "":
                                nickname = ANONYMOUS_HUMAN_HEADER
                    self.users.update({user_id: nickname})
                else:
                    nickname = self.users[user_id]
                human_header = "\n{}: ".format(nickname)
        else:
            human_header = ANONYMOUS_HUMAN_HEADER

        logger.debug("处理消息，发送人头部：{}".format(human_header))
