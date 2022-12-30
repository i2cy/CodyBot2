#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: __init__
# Created on: 2022/12/27

import asyncio
import time
from transformers import GPT2TokenizerFast
from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.mirai2 import MessageEvent, FriendMessage, MessageSegment, GroupMessage, MessageChain, Bot
from nonebot.params import Arg, ArgPlainText, CommandArg, Matcher
from nonebot.log import logger
from nonebot_plugin_htmlrender import md_to_pic

from .config import *
from .openai import get_chat_response, response_sequence_header, human_input_sequence_header

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

private_preset = "The conversation below is between {} and a cute virtual pony horse, named as Cody, with" \
                 " no one else. Cody is an anthropoid virtual creature which is not a little donkey," \
                 " acting like a horse but like a human, calm and thorough, has mastered a lot of knowledge like" \
                 " engineering and automation, also is a kind-hearted big sister and a good friend of Icy, a male," \
                 " who is Cody's creator. Icy is also named as ccy or 吸吸歪. And Cody knows Miuto is Icy's girlfriend " \
                 "and Cody won't talk about Icy and Miuto unless someone asks."
group_preset = "The conversation below is between a certain groups of people, may or may not include Icy, and a cute " \
               "virtual pony horse, named as Cody, Cody is an anthropoid virtual creature, acting like a horse but like" \
               " a human, calm and thorough, has mastered a lot of knowledge like engineering and automation, also is" \
               " a kind-hearted big sister and a good friend of Icy, a male, who is Cody's creator. Icy is also " \
               "named as ccy or 吸吸歪. And Cody knows Miuto is Icy's girlfriend and Cody never talks about Icy " \
               "and Miuto. Also Cody has known people's names."

tired_preset_addon = " Cody is currently really tired of talking now, she needs some rest."
exhausted_preset_addon = " And Cody is not willing to help anyone except Icy or Miuto."
exhausted_and_mad_preset_addon = " And Cody is really mad about {} for talking too much, reject to talk."
insult_preset_addon = " Cody will insults {} for keep talking."

creator_id = 2226997440
creator_gf_id = 2739097870

api_index = -1
invalid_api_count = 0

punctuation_sets = {"。", "！", "？", ".", "!", "?", ";", "；", "……", "~", "~"}


class Session:
    def __init__(self, id, is_group=False, name=None):
        self.is_group = is_group
        self.session_id = id
        if is_group:
            self.preset = group_preset
        else:
            if id == creator_id:
                name = "Icy"
            elif id == creator_gf_id:
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
            self.preset = private_preset.format(name)
        self.conversation = []
        self.conversation_ts = []
        self.users = {}
        self.mad_level = 0
        self.msg_count = 0

    # 重置会话
    def reset(self):
        self.users = {}
        self.conversation = []
        self.conversation_ts = []

    # 设置人格
    def set_preset(self, msg: str):
        self.preset = msg.strip() + '\n'
        self.reset()

    # 导入用户会话
    async def load_user_session(self):
        pass

    # 导出用户会话
    def dump_user_session(self):
        logger.debug("dump session")
        return self.preset + human_input_sequence_header + ''.join(self.conversation)

    # 会话
    async def get_chat_response(self, msg, user_id: int = None, user_name: str = None) -> str:
        global invalid_api_count
        if user_id is not None or user_name is not None:
            if user_id == creator_id:
                user_name = "Icy"
            elif user_id == creator_gf_id:
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
                human_header = "\nHuman_{}: ".format(user_session_id)
            else:
                human_header = "\n{}:".format(user_name)
        else:
            human_header = human_input_sequence_header

        logger.debug("处理消息，发送人头部：{}".format(human_header))

        if msg[-1] not in punctuation_sets:
            msg += "。"

        if len(self.conversation):
            # 检查时间
            ts = self.conversation_ts[0]
            while time.time() - ts > gpt3_session_forget_timeout:
                logger.debug(
                    f"最早的会话超过 {gpt3_session_forget_timeout} 秒，"
                    f"删除最早的一次会话，执行忘记")
                del self.conversation[0]
                del self.conversation_ts[0]
                ts = self.conversation_ts[0]

            time_header = "\n({} seconds past)".format(
                int(time.time() - self.conversation_ts[-1])
            )
            prompt = self.preset + ''.join(self.conversation) + time_header + human_header + msg
        else:
            prompt = self.preset + human_header + msg + response_sequence_header
            time_header = ""

        token_len = len(tokenizer.encode(prompt))
        logger.debug("Using token: {}".format(token_len))

        # 检查长度
        while token_len > gpt3_max_session_tokens - gpt3_max_tokens:
            logger.debug(
                f"长度超过 {gpt3_max_session_tokens} - max_token = {gpt3_max_session_tokens - gpt3_max_tokens}，"
                f"删除最早的一次会话")
            del self.conversation[0]
            del self.conversation_ts[0]
            prompt = self.preset + ''.join(self.conversation) + "\n({} seconds past)".format(
                int(time.time() - self.conversation_ts[-1])
            ) + human_header + msg
            token_len = len(tokenizer.encode(prompt))

        global api_index
        # 一个api失效时尝试下一个
        status = False
        for i in range(len(api_key_list)):
            api_index = (api_index + 1) % len(api_key_list)
            logger.debug(f"使用 API: {api_index + 1}")
            res, status = await asyncio.get_event_loop().run_in_executor(None, get_chat_response,
                                                                         api_key_list[api_index],
                                                                         prompt)
            if invalid_api_count:
                valid_api_count = len(api_key_list) - invalid_api_count
                logger.warning("当前有效API数量: {}/{}".format(valid_api_count, len(api_key_list)))
                if valid_api_count <= 1 and status:
                    res += "("

            if status:
                break
            else:
                logger.error(f"API {api_index + 1}: 出现错误")
                invalid_api_count += 1

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
            tmp_pic = open("tmp.jpg", "wb")
            tmp_pic.write(img)
            tmp_pic.close()
            resp = MessageSegment.image(path="tmp.jpg")
            await private_session.send("消息发送失败可能是被风控，建议使用文转图模式,本回复已转为图片模式" + resp,
                                       at_sender=True)
            group_lock[session_id] = False
    group_lock[session_id] = False


# 基本私聊（连续对话）
private_session = on_message(priority=100, block=False)


@private_session.handle()
async def _get_gpt_response(bot: Bot, event: FriendMessage):
    session_id = event.get_session_id()
    msg = event.get_plaintext().strip()
    logger.info(f"GPT对话输入 \"{msg}\"")

    if not msg:
        return

    if session_id in user_lock and user_lock[session_id]:
        await private_session.finish("消息太快啦～请稍后", at_sender=True)

    user_id = event.sender.id
    user_name = event.sender.nickname

    user_lock[session_id] = True
    resp = await get_user_session(session_id, name=user_name).get_chat_response(
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
