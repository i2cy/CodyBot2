#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: addons
# Created on: 2023/2/16

# TODO: reconstruct this file into GPT-3.5 mode

import time
from nonebot import get_bot, logger
from nonebot.adapters.onebot.v12 import Bot, MessageSegment, Message
from .session import SessionGPT3, SessionGPT35
from .api import CODY_HEADER
from .memory import Memory


class AddonBase:

    def __init__(self, session: SessionGPT35, presets: Memory, bot: Bot):
        """
        basic addon object parent
        :param session: SessionGPT35
        :param presets: Memory
        :param bot: Bot
        """

        self.addon_name = "AddonBase"
        self.session = session
        self.bot = bot


class BaseAddonManager:

    def __init__(self, session: SessionGPT3,
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
        addon_text = "An programmatic command is a text which must be placed separately in square brackets before " \
                     "Cody's reply. Multiple programmatic command can be placed at the same time separately. " \
                     "programmatic command formatted text should always uses half-width characters and no space " \
                     "between parameters. Cody will never try to ask others to use programmatic command or even talk " \
                     "about it. programmatic command text can only be added to reply in condition of below. Never " \
                     "quoting an programmatic command or its usage."

        if session_class.is_group:
            super().__init__(session_class, "", name_format_count=0, priority=2)
        else:
            super().__init__(session_class, addon_text, name_format_count=0, priority=2)


class ReminderAddon(BaseAddonManager):

    def __init__(self, session_class):
        addon_text = "Cody will remember a schedule when {} said, and never remember a schedule that has existed in " \
                     "Cody's memory. Cody can only use programmatic command formatted like \"[SC|<ADD/EDIT/REMOVE>" \
                     "|<unique integer schedule number>|<time of schedule>|<full description of event without " \
                     "subject>^#]\" to remember, edit or remove a schedule, time format like %Y-%m-%d %H:%M:%S. " \
                     "Conversation example: \"Human: 嗨。;Cody: 你好呀。;Human: 我明天早上9点有个会，帮我记一下。;Cody: [SC|ADD|1|2019-08-20 " \
                     "9:00:00|attend a meeting^#]好的，已经记下啦。\". Cody will always use plain text when quoting instead of " \
                     "programmatic command format. Never use programmatic command format when retelling or quoting."

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
                    if resp_f[-1] in ("[", "【"):
                        resp_f = resp_f[:-1]
                    resp_b = resp[end_ost:]
                    if resp_b[0] in ("]", "】"):
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
