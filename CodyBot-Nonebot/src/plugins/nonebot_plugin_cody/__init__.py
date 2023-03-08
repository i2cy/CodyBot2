#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: __init__
# Created on: 2022/12/27

import base64
from nonebot import on_message
from nonebot.adapters.mirai2 import FriendMessage, MessageSegment, GroupMessage, TempMessage, Bot
from nonebot_plugin_htmlrender import md_to_pic

from .addons import CommandAddon, ReminderAddon
from .config import *
from .presets import BUILTIN_PRIVATE_PRESET, BUILTIN_GROUP_PRESET, BUILTIN_PRIVATE_NSFW_PRESET
from .session import CREATOR_ID, CREATOR_GF_ID
from .api import get_chat_response, CODY_HEADER, ANONYMOUS_HUMAN_HEADER
from .session import Session, INVALID_APIs

REGISTERED_ADDONS = [CommandAddon, ReminderAddon]
# REGISTERED_ADDONS = []

user_session = {}
group_session = {}

user_lock = {}
group_lock = {}


def get_user_session(user_id, name=None) -> Session:
    if user_id not in user_session:
        user_session[user_id] = Session(user_id, name=name, addons=REGISTERED_ADDONS)
    return user_session[user_id]


def get_group_session(group_id) -> Session:
    if group_id not in group_session:
        group_session[group_id] = Session(group_id, is_group=True, addons=REGISTERED_ADDONS)
    return group_session[group_id]


# 基本群聊（连续对话）
group_chat_session = on_message(priority=50, block=False, rule=to_me())


@group_chat_session.handle()
async def _get_gpt_response(bot: Bot, event: GroupMessage):
    msg = event.get_plaintext().strip()
    group_id = event.sender.group.id
    session_id = group_id
    user_id = event.sender.id
    user_name = event.sender.name

    # 检查指令
    if len(msg) > 5 and msg[:5] == "i2cmd":
        if user_id in (CREATOR_ID, CREATOR_GF_ID):
            cmd = msg.split(" ")

            if len(cmd) > 2 and cmd[1] == "memory":
                # 重置会话
                if cmd[2] in ("reset", "Reset", "RESET"):
                    get_group_session(group_id).reset()
                    await group_chat_session.send("[memory has been cleared and reset]")
                else:
                    await group_chat_session.send("[unknown command]")

            elif len(cmd) > 1 and cmd[1] in ("api", "apikey", "status"):
                # 查询状态
                total_api_count = len(APIKEY_LIST)
                invalid_count = len(INVALID_APIs)
                status_text = "[API key status: {}/{}, integrity: {}%, invalid list: {}]".format(
                    total_api_count - invalid_count,
                    total_api_count,
                    int(100 * (total_api_count - invalid_count) / total_api_count),
                    ", ".join([str(i) for i in INVALID_APIs])
                )
                await group_chat_session.send(status_text)

            else:
                await group_chat_session.send("[unknown command]")

        else:
            await group_chat_session.finish("[permission denied]", at_sender=True)

        return

    logger.info(f"[group session {session_id}] GPT对话输入 \"{msg}\"")

    if not msg:
        return

    if session_id in group_lock and group_lock[session_id]:
        await group_chat_session.finish("[消息太快啦～请稍后]", at_sender=True)

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
            await private_session.send("[消息发送失败可能是被风控，建议使用文转图模式,本回复已转为图片模式]" + resp,
                                       at_sender=True)
            group_lock[session_id] = False
    group_lock[session_id] = False


# 群临时聊天
temp_session = on_message(priority=200, block=False)


@temp_session.handle()
async def _get_gpt_response(bot: Bot, event: TempMessage):
    await temp_session.send("抱歉，Cody目前并不支持临时会话聊天，若想与Cody私聊，请添加Cody为好友，并联系Icy通过审核")


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
                await private_session.send("[preset has set to nsfw, all conversation cleared]")
            else:
                get_user_session(user_id, name=user_name).set_preset(BUILTIN_PRIVATE_PRESET)
                await private_session.send("[preset has set to normal, all conversation cleared]")
        elif len(cmd) > 2 and cmd[1] == "memory":
            # 重置会话
            if cmd[2] in ("reset", "Reset", "RESET"):
                get_user_session(user_id, name=user_name).reset()
                await private_session.send("[memory has been cleared and reset]")
            else:
                await private_session.send("[unknown command]")

        elif len(cmd) > 1 and cmd[1] in ("api", "apikey", "status"):
            # 查询状态
            total_api_count = len(APIKEY_LIST)
            invalid_count = len(INVALID_APIs)
            status_text = "[API key status: {}/{}, integrity: {}%, invalid list: {}]".format(
                total_api_count - invalid_count,
                total_api_count,
                int(100 * (total_api_count - invalid_count) / total_api_count),
                ", ".join([str(i) for i in INVALID_APIs])
            )
            await group_chat_session.send(status_text)

        else:
            await private_session.send("[unknown command]")
        return

    logger.info(f"[session {session_id}] GPT对话输入 \"{msg}\"")

    if not msg:
        return

    if session_id in user_lock and user_lock[session_id]:
        await private_session.finish("[消息太快啦～请稍后]", at_sender=True)

    user_lock[session_id] = True
    resp = await get_user_session(user_id, name=user_name).get_chat_response(
        msg, user_id=user_id, user_name=user_name)

    # 发送消息
    # 如果是私聊直接发送
    if resp != "……":
        await private_session.send(resp, at_sender=True)

    user_lock[session_id] = False


# Cody初始化
def cody_init():
    pass


# 安全关闭
def cody_stop():
    for ele in user_session:
        user_session[ele].kill()
    for ele in group_session:
        group_session[ele].kill()


DRIVER.on_startup(cody_init)
DRIVER.on_shutdown(cody_stop)
