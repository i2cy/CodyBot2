#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: openai.py
# Created on: 2022/12/27

import asyncio
from typing import Awaitable

import openai
from .config import gpt3_max_tokens

response_sequence_header = "\nCody: "
human_input_sequence_header = "\nHuman: "


def get_chat_response(key, msg) -> tuple:
    openai.api_key = key
    try:
        response: dict = openai.Completion.create(
            model="text-davinci-003",
            prompt=msg,
            temperature=0.6,
            max_tokens=gpt3_max_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
            stop=[" Human:", " Cody:"]
        )
        res = response['choices'][0]['text'].strip()
        if response_sequence_header[1:] in res:
            res = res.split(response_sequence_header[1:])[-1]
        return res, True
    except Exception as e:
        return f"发生错误: {e}", False
