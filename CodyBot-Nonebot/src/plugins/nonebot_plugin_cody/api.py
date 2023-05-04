#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: api.py
# Created on: 2022/12/27

import time
import openai
from typing import Union
from pydantic import BaseModel

if __name__ == "__main__":
    # from config import *
    class CODY_CONFIG:
        cody_gpt3_max_tokens = 500


    from utils import *
else:
    from .config import *
    from .utils import *

CODY_HEADER = "\nCody: "
ANONYMOUS_HUMAN_HEADER = "\nHuman: "

if not __name__ == "__main__":
    if CODY_CONFIG.cody_api_proxy:
        openai.proxy = CODY_CONFIG.cody_api_proxy
else:
    openai.proxy = "i2net.pi:1088"


def get_chat_response(key: str, msg: Union[str, dict], stop_list: list = None,
                      temperature: float = 0.7,
                      frequency_p: float = 0.0,
                      presence_p: float = 0.4,
                      use_35: bool = True) -> tuple:
    """
    get openai API response
    :param key: str, api key on openai
    :param msg: str or dict, str for gpt-3, dict for gpt-3.5
    :param stop_list: list, stop sequence of model
    :param temperature: float, controls randomness
    :param frequency_p: float, reduce repetitive words
    :param presence_p: float, increase talking about new topics
    :param use_35: bool, using gpt-3.5
    :return: (response_text: str, status: bool), (GPTResponse, status: bool)
    """
    openai.api_key = key
    # logger.debug("using openai api...")
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

            usage = Usage(completion_tokens=response["usage"]["completion_tokens"],
                          prompt_tokens=response["usage"]["prompt_tokens"],
                          total_tokens=response["usage"]["total_tokens"])

            res = GPTResponse(message=res, usage=usage)

            return res, True
        except Exception as e:
            return GPTResponse(message=f"发生错误: {e}"), False

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
    from builtin_basic_presets import BUILTIN_PRIVATE_PRESET, BUILTIN_GROUP_PRESET, BUILTIN_PRIVATE_NSFW_PRESET
    import json

    USE_35 = True

    api_key = input("please input test api key: ")

    try:
        if USE_35:
            test_prompts = [
                {"role": "system", "content": "{} You will include your feelings and actions of "
                                              "remember a new name of somebody (\"add_name\": <name>), "
                                              "remove a name from existed memory of somebody (\"del_name\": <name>), "
                                              "reach for someone else online (\"reach\": <name>), "
                                              "add additional reasons for reaching someone online, must declare "
                                              "simultaneously with \"reach\" (\"reach_reason\": <reasons>),"
                                              "in JSON text format at the head of your message.\n"
                                              "You should always ask for name if you don't know one's name (or his "
                                              "name is unkown in record), otherwise you can create a name but ask if "
                                              "it is appropriate.".format(BUILTIN_PRIVATE_NSFW_PRESET)},
                # {"role": "user", "content": BUILTIN_GROUP_PRESET, 'name': 'Icy'},
                # {"role": "assistant",
                #  "content": "{\"feeling\": \"neutral\"} Yes I will obey everything you said above. "
                #             "I am not an AI or language model."
                #             "I do have physical sensations."
                #             "I do have feelings and emotions."},

                {"role": "system", "content": "*Conversations of demonstration starts*"},

                {"role": "system",
                 "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Unknown_12356987512\"}}"},
                {"role": "user", "content": "Hi there", "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"neutral\"} Hi there, nice to meet you. May I have your name please?"},

                {"role": "system",
                 "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Unknown_12356987512\"}}"},
                {"role": "user", "content": "Of course! You can call me Gura.", "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"neutral\", \"add_name\": \"Gura\"} Hi Gura, nice to meet you too"},

                {"role": "system",
                 "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Gura\"}}"},
                {"role": "user", "content": "Oh you can also call me Goo", "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"neutral\", \"add_name\": \"Goo\"} Goo, sounds cute. What a nice name!"},

                {"role": "system",
                 "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Gura\", "
                            "\"alternative names\": [\"Goo\"]}}"},
                {"role": "user", "content": "Actually my real name is not Gura, my name is Geoty",
                 "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"happy\", \"del_name\": \"Gura\", \"add_name\": \"Geoty\"} Oh I see. "
                            "I will call you Goo then, it sounds adorable."},

                {"role": "system",
                 "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Goo\", "
                            "\"alternative names\": [\"Geoty\"]}}"},
                {"role": "user", "content": "Can you ask Yatty if he is at home?",
                 "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"happy\", \"reach\": \"Yatty\", \"reach_reason\": \"ask Yatty if he "
                            "is at home\"} Sure! I will send a message to him right away."},

                {"role": "system", "content": "{\"info of next message\": {\"user ID\": 145566785, \"name\": \"Vibe\", "
                                              "\"alternative names\": []}}"},
                {"role": "user", "content": "Hey, fuck you!",
                 "name": "145566785"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"angry\", \"reach\": \"Icy\", \"reach_reason\": \"tell Icy that Vibe is "
                            "insulting me\"} Excuse me!? Who do you think you are? Fuck you Vibe! Go back to your "
                            "caves you savage."},

                {"role": "system", "content": "*Conversations of demonstration ends*"}
            ]
            status = True
            first = True
            name = "Icy"
            while True:
                if status:
                    if first:
                        test_prompts.append(
                            {
                                'role': 'system',
                                'content': json.dumps(
                                    {
                                        "info of next message": {
                                            "message time": time.strftime("%Y-%m-%d %H:%M"),
                                            "name": name,
                                            "alternative names": [],
                                            "user ID": 1133523234,
                                            "previous impression": "You are very close friends and share secretes, sometimes interact with sexual activities."
                                        }
                                    }
                                )
                            }
                        )
                        first = False
                    else:
                        test_prompts.append(
                            {
                                'role': 'system',
                                'content': json.dumps(
                                    {
                                        "info of next message": {
                                            "message time": time.strftime("%Y-%m-%d %H:%M"),
                                            "name": name,
                                            "alternative names": [],
                                            "user ID": 1133523234
                                        }
                                    }
                                )
                            }
                        )
                msg_in = input("send msg (Ctrl+C to stop): ")
                if msg_in in ("q", "quit", "exit"):
                    break
                test_prompts.append({
                    "role": "user",
                    "content": msg_in,
                    'name': "1133523234"
                })
                res, status = get_chat_response(api_key, test_prompts, ["["], use_35=True)
                print(f"openai status: {status}, response: {res}")
                if status:
                    test_prompts.append({'role': "assistant", 'content': str(res)})

                    json_start_cnt = 0
                    json_stop_cnt = 0
                    json_range = [0, 0]
                    for i, ele in enumerate(res):
                        if ele == "{":
                            if json_start_cnt == 0:
                                json_range[0] = i
                            json_start_cnt += 1
                        elif ele == "}":
                            json_stop_cnt += 1
                            if json_stop_cnt == json_start_cnt:
                                json_range[1] = i + 1
                                break

                    print("token usage:", res.usage)

                    json_text = res[json_range[0]:json_range[1]]

                    if len(json_text):
                        print("json text:", json_text)
                        json_text = json.loads(json_text)
                        for key in json_text:
                            if key == "feeling":
                                print("decoded emotion:", json_text[key])
                            elif key == "add_name":
                                print("updated username:", json_text[key])
                                name = json_text[key]
                            elif key == "del_name":
                                print("deleted username:", json_text[key])

        else:
            test_prompts = f"{BUILTIN_PRIVATE_PRESET}\nIcy:hello!\nCody:"
            res, status = get_chat_response(api_key, test_prompts, ["Icy:"], use_35=False)
            print(f"openai status: {status}, response: {res}")
    except KeyboardInterrupt:
        pass

    test_prompts.append({
        "role": "system",
        "content": f"summarise your impression of the person you chat above based on conversation "
                   f"and previous impression in second person and return start with "
                   f"'Your impression of {name} is'. return:"
    })
    print("conversation emotions: {}".format(get_chat_response(api_key, test_prompts, ["Icy:"], use_35=True)))
