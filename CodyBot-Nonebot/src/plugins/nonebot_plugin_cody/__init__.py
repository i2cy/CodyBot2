#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: __init__
# Created on: 2022/12/27

import asyncio
import time
import base64
from transformers import GPT2TokenizerFast
from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.mirai2 import MessageEvent, FriendMessage, MessageSegment, GroupMessage, TempMessage, Bot
from nonebot.params import Arg, ArgPlainText, CommandArg, Matcher
from nonebot.log import logger
from nonebot_plugin_htmlrender import md_to_pic
from .config import *
from .presets import BUILTIN_PRIVATE_PRESET, BUILTIN_GROUP_PRESET, BUILTIN_PRIVATE_NSFW_PRESET, BUILTIN_MAD_PRESETS
from .presets import CommandAddon, ReminderAddon
from .openai import get_chat_response, response_sequence_header, human_input_sequence_header

_CREATOR_ID = 2226997440
_CREATOR_GF_ID = 2739097870

REGISTERED_ADDONS = []

_TOKENIZER = GPT2TokenizerFast.from_pretrained("gpt2")
API_INDEX = -1
INVALID_API_COUNT = 0
PUNCTUATION_SETS = {"。", "！", "？", ".", "!", "?", ";", "；", "……", "~", "~"}


class Session:
    def __init__(self, id, is_group=False, name=None):
        self.is_group = is_group
        self.session_id = id
        if is_group:
            self.preset = BUILTIN_GROUP_PRESET
            self.name = "us"
        else:
            if id == _CREATOR_ID:
                name = "Icy"
            elif id == _CREATOR_GF_ID:
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
            self.preset = BUILTIN_PRIVATE_PRESET.format(name)

        self.addons = [ele() for ele in REGISTERED_ADDONS]

        self.conversation = []
        self.conversation_ts = []
        self.conversation_mad_span_tokens = []
        self.conversation_mad_span_ts = []
        self.max_session_tokens = gpt3_max_session_tokens
        self.users = {}
        self.mad_time_span = gpt3_cody_initial_mad_level_change_time_span
        self.mad_threshold = gpt3_cody_mad_level_change_msg_count_threshold
        self.mad_speedup_rate = gpt3_cody_mad_level_speedup_gamma
        self.mad_release_rate = gpt3_cody_mad_level_release_rate
        self.mad_status_change_ts = 0

        self.mad_level = 0
        self.msg_count = 0

    # 重置会话
    def reset(self):
        self.users = {}
        self.conversation = []
        self.conversation_ts = []

    def emotional_change_of_preset(self) -> str:
        time_span = self.mad_time_span * (self.mad_speedup_rate ** (self.mad_level + 1))
        threshold = self.mad_threshold * (self.mad_speedup_rate ** (self.mad_level + 1))
        release_threshold = self.mad_release_rate * threshold

        # 检查时间
        if len(self.conversation_mad_span_ts):
            ts = self.conversation_mad_span_ts[0]

            while time.time() - ts > self.mad_time_span:
                del self.conversation_mad_span_ts[0]
                del self.conversation_mad_span_tokens[0]
                if len(self.conversation_mad_span_ts):
                    ts = self.conversation_mad_span_ts[0]
                else:
                    break

        criterion = 0
        t_now = time.time()
        for i, ele in enumerate(self.conversation_mad_span_ts):
            if t_now - ele < time_span:
                criterion += self.conversation_mad_span_tokens[i]
        logger.debug("[ID: {}] emotional criterion value: {}".format(self.session_id, criterion))

        # 检查阈值
        time_span_full_filled = (time.time() - self.mad_status_change_ts) > time_span
        even_madder = criterion > (gpt3_max_session_tokens * threshold)
        even_madder &= time_span_full_filled
        release_temper = criterion < (gpt3_max_session_tokens * release_threshold)
        release_temper &= time_span_full_filled

        if even_madder:
            self.mad_level += 1
            if self.mad_level > 5:
                self.mad_level = 5
            self.mad_status_change_ts = time.time()
            logger.info("Cody in session ID: {} changed her temper up to {}".format(self.session_id, self.mad_level))

        elif release_temper:
            time_span = self.mad_time_span * (self.mad_speedup_rate ** (self.mad_level + 1))
            while time.time() - self.mad_status_change_ts > time_span:
                self.mad_status_change_ts += time_span
                self.mad_level -= 1
                if self.mad_level <= 0:
                    break
                time_span = self.mad_time_span * (self.mad_speedup_rate ** (self.mad_level + 1))
            if self.mad_level < 0:
                self.mad_level = 0
            self.mad_status_change_ts = time.time()
            logger.info("Cody in session ID: {} changed her temper down to {}".format(self.session_id, self.mad_level))

        # 修改情绪
        real_temper = self.mad_level - 1

        if self.name in ("Icy", "Miuto"):
            if self.mad_level > 2:
                real_temper = 2

        ret = self.preset

        if real_temper >= 0:
            addon = BUILTIN_MAD_PRESETS[real_temper].format(self.name)
            ret += addon

            logger.debug("[ID: {}], mad level: {}".format(self.session_id, real_temper))

        return ret

    # 设置人格
    def set_preset(self, msg: str):
        self.preset = msg
        self.reset()

    def __get_preset(self, preset):
        for ele in self.addons:
            preset = ele(preset)
        return preset

    # 导入用户会话
    async def load_user_session(self):
        pass

    # 导出用户会话
    def dump_user_session(self):
        logger.debug("dump session")
        return self.preset + human_input_sequence_header + ''.join(self.conversation)

    # 会话
    async def get_chat_response(self, msg, user_id: int = None, user_name: str = None) -> str:
        global INVALID_API_COUNT
        if user_id is not None or user_name is not None:
            if user_id == _CREATOR_ID:
                user_name = "Icy"
            elif user_id == _CREATOR_GF_ID:
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
            human_header = human_input_sequence_header

        logger.debug("处理消息，发送人头部：{}".format(human_header))

        if msg[-1] not in PUNCTUATION_SETS:
            msg += "。"

        # 检查情绪
        preset = self.emotional_change_of_preset()
        time_header = "\n({})".format(
            time.strftime("%Y-%m-%d %A %H:%M:%S")
        )
        preset = self.__get_preset(preset)

        if len(self.conversation):
            # 检查时间
            ts = self.conversation_ts[0]
            while time.time() - ts > gpt3_session_forget_timeout:
                logger.debug(
                    f"最早的会话超过 {gpt3_session_forget_timeout} 秒，"
                    f"删除最早的一次会话，执行忘记")
                del self.conversation[0]
                del self.conversation_ts[0]
                if len(self.conversation_ts):
                    ts = self.conversation_ts[0]
                else:
                    break

            prompt = preset + ''.join(self.conversation) + time_header + human_header + msg
        else:
            prompt = preset + time_header + human_header + msg + response_sequence_header

        token_len = len(_TOKENIZER.encode(prompt))
        logger.debug("Using token: {}".format(token_len))

        # 检查长度
        while token_len > gpt3_max_session_tokens - gpt3_max_tokens:
            logger.debug(
                f"长度超过 {gpt3_max_session_tokens} - max_token = {gpt3_max_session_tokens - gpt3_max_tokens}，"
                f"删除最早的一次会话")
            del self.conversation[0]
            del self.conversation_ts[0]
            prompt = preset + ''.join(self.conversation) + time_header + human_header + msg
            token_len = len(_TOKENIZER.encode(prompt))

        self.conversation_mad_span_ts.append(time.time())
        self.conversation_mad_span_tokens.append(token_len)

        global API_INDEX
        # 一个api失效时尝试下一个
        status = False
        for i in range(len(api_key_list)):
            API_INDEX = (API_INDEX + 1) % len(api_key_list)
            logger.debug(f"使用 API: {API_INDEX + 1}")
            res, status = await asyncio.get_event_loop().run_in_executor(None, get_chat_response,
                                                                         api_key_list[API_INDEX],
                                                                         prompt, human_header[1:-1])
            if INVALID_API_COUNT:
                valid_api_count = len(api_key_list) - INVALID_API_COUNT
                logger.warning("当前有效API数量: {}/{}".format(valid_api_count, len(api_key_list)))
                if valid_api_count <= 1 and status:
                    res += "("

            if status:
                break
            else:
                logger.error(f"API {API_INDEX + 1}: 出现错误")
                INVALID_API_COUNT += 1

        if status:
            if not res.replace(" ", ""):
                res = "……"
            logger.debug("AI 返回：{}".format(res))
            self.conversation.append(f"{time_header}{human_header}{msg}{response_sequence_header}{res}")
            self.conversation_ts.append(time.time())
            logger.debug("当前对话（ID:{}）: {}".format(self.session_id, self.conversation))
        else:
            # 超出长度或者错误自动重置
            self.reset()

        return res

    # 连续会话
    async def continuous_session(self):
        pass


user_session = {}


def get_user_session(user_id, name=None) -> Session:
    if user_id not in user_session:
        user_session[user_id] = Session(user_id, name=name)
    return user_session[user_id]


group_session = {}


def get_group_session(group_id) -> Session:
    if group_id not in group_session:
        group_session[group_id] = Session(group_id, is_group=True)
    return group_session[group_id]


user_lock = {}
group_lock = {}

# 基本群聊（连续对话）
group_chat_session = on_message(priority=50, block=False, rule=to_me())


@group_chat_session.handle()
async def _get_gpt_response(bot: Bot, event: GroupMessage):
    msg = event.get_plaintext().strip()
    logger.info(f"Group GPT对话输入 \"{msg}\"")
    group_id = event.sender.group.id
    session_id = group_id
    user_id = event.sender.id
    user_name = event.sender.name

    if not msg:
        return

    if session_id in group_lock and group_lock[session_id]:
        await group_chat_session.finish("消息太快啦～请稍后", at_sender=True)

    group_lock[session_id] = True
    resp = "……"
    for i in range(2):
        resp = await get_group_session(group_id).get_chat_response(msg, user_id=user_id, user_name=user_name)
        if resp != "……":
            break

    # 发送消息
    if resp != "……":
        message_id = event.source.id
        group_id = event.sender.group.id
        msg_chain = event.message_chain
        sender_id = event.sender.id
        try:
            await group_chat_session.send(MessageSegment.quote(message_id, group_id,
                                                               sender_id, target_id=sender_id,
                                                               origin=msg_chain) + resp, at_sender=False)
        except:
            img = await md_to_pic(resp)
            img = base64.b64encode(img).decode()
            resp = MessageSegment.image(base64=img)
            await private_session.send("消息发送失败可能是被风控，建议使用文转图模式,本回复已转为图片模式" + resp,
                                       at_sender=True)
            group_lock[session_id] = False
    group_lock[session_id] = False


# 群临时聊天
temp_session = on_message(priority=200, block=False)


async def _get_gpt_response(bot: Bot, event: TempMessage):
    await temp_session.send("抱歉，Cody目前并不支持临时会话聊天，若想和Cody私聊，请添加Cody为好友，并联系Icy通过审核")


# 基本私聊（连续对话）
private_session = on_message(priority=100, block=False)


@private_session.handle()
async def _get_gpt_response(bot: Bot, event: FriendMessage):
    session_id = event.get_session_id()
    msg = event.get_plaintext().strip()
    user_id = event.sender.id
    user_name = event.sender.nickname

    # 检查指令
    if len(msg) > 5 and msg[:5] == "i2cmd":
        cmd = msg.split(" ")
        if len(cmd) > 2 and cmd[1] == "preset":
            # 切换成nsfw人格（测试）
            if cmd[2] in ("nsfw", "horny"):
                get_user_session(user_id, name=user_name).set_preset(BUILTIN_PRIVATE_NSFW_PRESET)
                await private_session.send("preset has set to nsfw")
            else:
                get_user_session(user_id, name=user_name).set_preset(BUILTIN_PRIVATE_PRESET)
                await private_session.send("preset has set to normal")
        return

    logger.info(f"GPT对话输入 \"{msg}\"")

    if not msg:
        return

    if session_id in user_lock and user_lock[session_id]:
        await private_session.finish("消息太快啦～请稍后", at_sender=True)

    user_lock[session_id] = True
    resp = await get_user_session(user_id, name=user_name).get_chat_response(
        msg, user_id=user_id, user_name=user_name)

    # 如果开启图片渲染，且字数大于limit则会发送图片
    if gpt3_image_render and len(resp) > gpt3_image_limit:
        if resp.count("```") % 2 != 0:
            resp += "\n```"
        img = await md_to_pic(resp)
        tmp_pic = open("tmp.jpg", "wb")
        tmp_pic.write(img)
        tmp_pic.close()
        resp = MessageSegment.image(path="tmp.jpg")

    # 发送消息
    # 如果是私聊直接发送
    if resp != "……":
        await private_session.send(resp, at_sender=True)

    user_lock[session_id] = False
