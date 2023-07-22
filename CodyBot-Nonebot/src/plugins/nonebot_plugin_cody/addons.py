#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: addons
# Created on: 2023/2/16

import time
import json
from nonebot import get_bot, logger
from nonebot.adapters.onebot.v12 import Bot, MessageSegment, Message
from .session import SessionGPT3, SessionGPT35
from .api import CODY_HEADER
from .memory import Memory


class AddonBase:

    def __init__(self, session: SessionGPT35):
        """
        basic addon object parent
        :param session: SessionGPT35
        """

        self.addon_name = "AddonBase"
        self.session = session
        self.bot = self.session.bot

    def log(self, log_message: str):
        """
        add one line of log information to system logger
        :param log_message: str
        :return:
        """
        self.session.log(f'[{self.addon_name}] {log_message}')

    def alarm_callback(self, *args, **kwargs):
        """
        basic alarm callback function. calls when registered alarm in session triggered.
        :param args: Any
        :param kwargs: Any
        :return: Any
        """
        pass

    def user_msg_post_proc_callback(self):
        """
        basic user message post-processing callback method. calls when a user send message to Cody
        :return: None
        """
        pass

    def cody_msg_post_proc_callback(self):
        """
        basic cody message post-processing callback method. calls when received a new feedback from gpt
        :return: None
        """
        pass


# TODO: create an default addon that used for updating user name, decode reach command, update impressions

class DefaultsAddon(AddonBase):

    def extract_json_from_cody_response(self) -> dict or None:
        """
        extract json dict from cody's message
        :return: dict
        """
        # copy message content from session.conversation
        msg = self.session.conversation.cody_msg

        json_start_cnt = 0
        json_stop_cnt = 0
        json_range = [0, 0]
        # locate the start and tail of json text
        for i, ele in enumerate(msg):
            if ele == "{":
                if json_start_cnt == 0:
                    json_range[0] = i
                json_start_cnt += 1
            elif ele == "}":
                json_stop_cnt += 1
                if json_stop_cnt == json_start_cnt:
                    json_range[1] = i + 1
                    break

        # copy json text
        json_text = msg[json_range[0]:json_range[1]]

        # decode and transfer
        ret = None
        if len(json_text):
            try:
                ret = json.loads(json_text)
            except Exception as err:
                # log error when failed to decode json and return None
                self.log("[ERROR] failed to decode json text from Cody's response, {}, json text: {}".format(
                    err, json_text
                ))

        return ret

    def cody_msg_post_proc_callback(self):
        """
        decode emotion feelings, name update
        :return: None
        """
        # try to get json text from
        res = self.extract_json_from_cody_response()

        if res is None:
            # if no json message decoded, skip
            return

        # get essential information of conversation
        is_group = self.session.is_group
        user_id = self.session.conversation.cody_msg_extra['user_id']
        timestamp = self.session.conversation.cody_msg_extra['timestamp']
        group_id = self.session.id

        # decode keywords
        for key in res:
            if key == "feeling":
                # feeling process
                # TODO: add feeling processing system
                pass
            elif key == "add_name":
                # update name in impression database
                old_frame = self.session.impression.get_individual(user_id)

                if "UNKNOWN" in old_frame.name.upper():
                    # if user's name is unknown, replace it with current updated name
                    self.session.impression.update_individual(user_id, name=res[key])
                else:
                    # else alter the old name to alternatives
                    self.session.impression.update_individual(
                        user_id,
                        name=res[key],
                        alternatives=old_frame.alternatives.append(old_frame.name)
                    )





# TODO: reconstruct ReminderAddon to fit new addon base

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
