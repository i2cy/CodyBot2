#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: api.py
# Created on: 2022/12/27

import openai

if __name__ == "__main__":
    pass


    # from config import *
    class CODY_CONFIG:
        cody_gpt3_max_tokens = 500
else:
    from .config import *

CODY_HEADER = "\nCody: "
ANONYMOUS_HUMAN_HEADER = "\nHuman: "

if not __name__ == "__main__":
    if CODY_CONFIG.cody_api_proxy:
        openai.proxy = CODY_CONFIG.cody_api_proxy
else:
    openai.proxy = "i2net.pi:1088"


def get_chat_response(key, msg, stop_list=None,
                      temperature=0.7,
                      frequency_p=0.0,
                      presence_p=0.4,
                      use_35=True) -> tuple:
    openai.api_key = key
    # logger.debug("using openai api...")
    if stop_list is None:
        stop_list = []
    if use_35:
        try:
            response: dict = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=msg,
                temperature=temperature,
                max_tokens=CODY_CONFIG.cody_gpt3_max_tokens,
                top_p=1,
                frequency_penalty=frequency_p,
                presence_penalty=presence_p,
                stop=stop_list
            )
            res = response['choices'][0]['message']['content'].strip()

            if CODY_HEADER[1:-1] in res or CODY_HEADER[1:-1].replace(":", "：") in res:
                res = res.split(CODY_HEADER[1:-1])[-1]
                res = res.split(CODY_HEADER[1:-1].replace(":", "："))[-1]
            while len(res) and res[0] == " ":
                res = res[1:]

            return res, True
        except Exception as e:
            return f"发生错误: {e}", False

    else:
        try:
            response: dict = openai.Completion.create(
                model="text-davinci-003",
                prompt=msg,
                temperature=temperature,
                max_tokens=CODY_CONFIG.cody_gpt3_max_tokens,
                top_p=1,
                frequency_penalty=frequency_p,
                presence_penalty=presence_p,
                stop=stop_list
            )
            res = response['choices'][0]['text'].strip()
            if CODY_HEADER[1:-1] in res or CODY_HEADER[1:-1].replace(":", "：") in res:
                res = res.split(CODY_HEADER[1:-1])[-1]
                res = res.split(CODY_HEADER[1:-1].replace(":", "："))[-1]
            while len(res) and res[0] == " ":
                res = res[1:]
            return res, True
        except Exception as e:
            return f"发生错误: {e}", False


if __name__ == '__main__':
    from presets import BUILTIN_PRIVATE_PRESET, BUILTIN_GROUP_PRESET

    USE_35 = True

    key = input("please input test api key: ")

    if USE_35:
        test_prompts = [
            {"role": "system", "content": BUILTIN_GROUP_PRESET},
            {"role": "system", "content": "[message info: {message time: UTC+8 2022/08/28 19:11, "
                                          "name: Icy, user_id: 2226997440, relationship: creator}]"},
            {"role": "user", "content": "hello!", 'name': "2226997440"},
            {"role": "assistant", "content": "Hi Icy! It's so nice to see you! How are you doing today?"},
            {"role": "system",
             "content": "[message info: {message time: UTC+8 2022/08/28 19:53, "
                        "name: 齐博宇, user_id: 1133523234, relationship: enemy}]"},
            {"role": "user",
             "content": "you again, remember when was the time we last met? and who are you again? are you an AI?",
             'name': "1133523234"},
        ]
        res, status = get_chat_response(key, test_prompts, ["[UTC+8"], use_35=True)
        print(f"openai status: {status}, response: {res}")
    else:
        test_prompts = f"{BUILTIN_PRIVATE_PRESET}\nIcy:hello!\nCody:"
        res, status = get_chat_response(key, test_prompts, ["Icy:"], use_35=False)
        print(f"openai status: {status}, response: {res}")
