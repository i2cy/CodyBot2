#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: api.py
# Created on: 2022/12/27
import time

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
            print(response)
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
    import json

    USE_35 = True

    api_key = input("please input test api key: ")

    try:
        if USE_35:
            test_prompts = [
                {"role": "system", "content": "You will include your feelings and actions of "
                                              "remember a new name of somebody (\"add_name\": <name>), "
                                              "remove a name from existed memory of somebody (\"del_name\": <name>), "
                                              "reach for someone else online (\"reach\": <name>), "
                                              "add additional reasons for reaching someone online, must declare simultaneously with \"reach\" (\"reach_reason\": <reasons>), "
                                              "in JSON text format at the head of your message.\n"
                                              "You should always ask for name if you don't know one's name, "
                                              "otherwise you can create a name but ask if it is appropriate."},
                {"role": "user", "content": BUILTIN_GROUP_PRESET, 'name': 'Icy'},
                {"role": "assistant",
                 "content": "{\"feeling\": \"neutral\"} Yes I will obey everything you said above. "
                            "I am not an AI or language model."
                            "I do have physical sensations."
                            "I do have feelings and emotions."},

                {"role": "system", "content": "*Conversations of demonstration starts*"},
                {"role": "system", "content": "[info of next message: {name: Unknown, user_id: 12356987512}]"},
                {"role": "user", "content": "Hi there, my name is Gura nice to meet you", "name": "12356987512"},

                {"role": "assistant",
                 "content": "{\"feeling\": \"neutral\", \"add_name\": \"Gura\"} Hi Gura, nice to meet you too"},

                {"role": "system", "content": "[info of next message: {name: Gura, user_id: 12356987512}]"},
                {"role": "user", "content": "Oh you can also call me Goo", "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"neutral\", \"add_name\": \"Goo\"} Goo, sounds cute. What a nice name!"},

                {"role": "system", "content": "[info of next message: {name: Gura, alternative names: [Goo], "
                                              "user_id: 12356987512}]"},
                {"role": "user", "content": "Actually my real name is not Gura, my name is Geoty",
                 "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"happy\", \"del_name\": \"Gura\", \"add_name\": \"Geoty\"} Oh I see. "
                            "I will call you Goo then, it sounds adorable."},
                {"role": "system", "content": "[info of next message: {name: Goo, alternative names: [Geoty], "
                                              "user_id: 12356987512}]"},
                {"role": "user", "content": "Can you ask Yatty if he is at home?",
                 "name": "12356987512"},
                {"role": "assistant",
                 "content": "{\"feeling\": \"happy\", \"reach\": \"Yatty\", \"reach_reason\": \"ask Yatty if he "
                            "is at home\"} Sure! I will send a message to him right away."},
                {"role": "system", "content": "*Conversations of demonstration ends*"}
                # {"role": "system", "content": "[info of next message: {message time: 2022-08-28 19:11, "
                #                                "name: Icy, user_id: 2226997440, Icy is your creator}]"},
                # {"role": "user", "content": "hello!", 'name': "2226997440"},
                # {"role": "assistant", "content": "Hi Icy! It's so nice to see you! How are you doing today?"},
                # {"role": "system",
                # "content": "[info of next message: {message time: 2022-08-28 19:53, "
                #             "name: Yatty, user_id: 1133523234, Yatty is your stranger}]"},
                # {"role": "user",
                #  "content": "hello, remember when was the time we last met? and who are you again? are you an AI?",
                #  'name': "1133523234"},
            ]
            status = True
            first = True
            name = "Miuto"
            while True:
                if status:
                    if first:
                        test_prompts.append({
                            'role': 'system',
                            'content': "[info of next message: {" + "message time: {}, name:"
                                                                    " {}, user_id: 1133523234, {}".format(
                                time.strftime("%Y-%m-%d %H:%M"),
                                name,
                                "Your impression of Miuto is that she seems to be feeling frustrated and concerned about "
                                "her inability to reach Icy. She is looking for any possible solutions or insights you "
                                "may have, and is open to discussing her feelings with you."
                            ) + "}]",
                        })
                        first = False
                    else:
                        test_prompts.append({
                            'role': 'system',
                            'content': "[info of next message: {" + "message time: {}, name:"
                                                                    " {}, user_id: 1133523234".format(
                                time.strftime("%Y-%m-%d %H:%M"),
                                name
                            ) + "}]",
                        })
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
                    test_prompts.append({'role': "assistant", 'content': res})

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
