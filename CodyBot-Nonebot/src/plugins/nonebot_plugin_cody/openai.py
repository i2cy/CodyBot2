#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: openai.py
# Created on: 2022/12/27


import openai
from .config import *

CODY_HEADER = "\nCody:"
ANONYMOUS_HUMAN_HEADER = "\nHuman:"


def get_chat_response(key, msg, stop_list,
                      temperature=0.7,
                      frequency_p=0.0,
                      presence_p=0.4) -> tuple:

    openai.api_key = key
    logger.debug("using openai api...")
    if stop_list is None:
        stop_list = []
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
        if CODY_HEADER[1:] in res or CODY_HEADER[1:].replace(":", "：") in res:
            res = res.split(CODY_HEADER[1:])[-1]
            res = res.split(CODY_HEADER[1:].replace(":", "："))[-1]
        while len(res) and res[0] == " ":
            res = res[1:]
        return res, True
    except Exception as e:
        return f"发生错误: {e}", False
