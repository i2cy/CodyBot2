#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: presets
# Created on: 2023/2/16

import json
import time
import tiktoken
from pydantic import BaseModel

if __name__ == "__main__":
    from utils import GPTResponse, TimeStamp
    from session import SessionGPT35
else:
    from .utils import GPTResponse, TimeStamp
    from .session import SessionGPT35


class ExtraTypes:
    user_msg: int = 0
    user_msg_info: int = 1
    cody_msg: int = 2


class Memory(BaseModel):
    basic: str = "Your name is Cody."  # basic preset information of session
    actions: list = [
        "remember a new name of somebody (\"add_name\": <name>)",
        "remove a name from existed memory of somebody (\"del_name\": <name>)",
        "reach for someone else online (\"reach\": <name>)",
        "add additional reasons for reaching someone online, must declare simultaneously with \"reach\" ("
        "\"reach_reason\": <reasons>)",
    ]  # extended preset of actions format
    extensions: list = [
        "You must ask for name if you don't know one's name (or his name is unknown in message information), "
        "otherwise you can create a name but ask if it is appropriate. You will insult people who has bad manners."
    ]  # extra announcement for actions

    conversation_examples: list = [
        [{"role": "system",
          "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Unknown_12356987512\"}}"},
         {"role": "user", "content": "Hi there. Who are you.", "name": "12356987512"},
         {"role": "assistant",
          "content": "{\"feeling\": \"neutral\"} I am Cody, nice to meet you. May I have your name please?"},

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

         {"role": "system", "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Gura\", "
                                       "\"alternative names\": [\"Goo\"]}}"},
         {"role": "user", "content": "Actually my real name is not Gura, my name is Geoty",
          "name": "12356987512"},
         {"role": "assistant",
          "content": "{\"feeling\": \"happy\", \"del_name\": \"Gura\", \"add_name\": \"Geoty\"} Oh I see. "
                     "I will call you Goo then."},

         {"role": "system", "content": "{\"info of next message\": {\"user ID\": 12356987512, \"name\": \"Goo\", "
                                       "\"alternative names\": [\"Geoty\"]}}"},
         {"role": "user", "content": "Can you ask Yatty if he is at home?",
          "name": "12356987512"},
         {"role": "assistant",
          "content": "{\"feeling\": \"happy\", \"reach\": \"Yatty\", \"reach_reason\": \"ask Yatty if he "
                     "is at home\"} Sure! I will send a message to him right away."}],

        [{"role": "system", "content": "{\"info of next message\": {\"user ID\": 145566785, \"name\": \"Vibe\", "
                                       "\"alternative names\": []}}"},
         {"role": "user", "content": "Hey, fuck you!",
          "name": "145566785"},
         {"role": "assistant",
          "content": "{\"feeling\": \"sarcastic\", \"reach\": \"Icy\", \"reach_reason\": \"tell Icy that Vibe is "
                     "insulting me\"} Look what we have got here. Oh, it's you, savage Vibe. I see you have came out "
                     "from your cage, where is your master by the way?"}],
    ]  # example conversation example

    conversation: list = []  # conversation dict in memory
    conversation_extra: list = []  # extra information about each element in conversations

    used_token_score: int = 0  # summary of tokens that current prompts cost
    max_token_limit: int = 16_384  # max token score limit setting

    # -*- temporaries -*-

    user_msg: str = ""  # user message temporary storage
    user_msg_info: dict = {}  # information of user message which is ahead of user message content

    # extra information about user_msg, default keywords: type=ExtraTypes.user_msg, user_id, username, timestamp
    user_msg_extra: dict = {}
    # extra information about user_msg_info, default keywords: type=ExtraTypes.user_msg_info, user_id, timestamp(same)
    user_msg_info_extra: dict = {}

    cody_msg: GPTResponse or None = None  # cody message temporary storage

    # extra information about cody_msg_extra, default keywords: type=ExtraTypes.cody_msg, user_id, timestamp(same)
    cody_msg_extra: dict = {}

    user_msg_post_proc: list = []  # list of functions that will be called every time calling 'add_user_message' method
    cody_msg_post_proc: list = []  # list of functions that will be called every time parsing a GPTResponse

    logger: None = None
    session: SessionGPT35 = None

    def set_parent(self, session: SessionGPT35):
        """
        set parent session class for memory class
        :param session: SessionGPT35
        :return:
        """
        self.session = session

    def set_max_token_limit(self, max_token_limit: int):
        """
        set max token limit for conversation
        :param max_token_limit: int
        :return:
        """
        self.max_token_limit = max_token_limit

    def set_logger(self, logger):
        """
        set logger function
        :param logger: Function
        :return:
        """
        self.logger = logger

    def __log(self, log_message: str):
        """
        internal logger redirector
        :param log_message: str
        :return:
        """
        if self.logger is not None:
            self.logger(f'[memory] {log_message}')

    def __save_and_clear_temp_msg(self):
        """
        save temporarily saved message segment
        :return:
        """
        if self.user_msg:
            # if user_msg was stored before, save it and clear it
            self.conversation.extend(self.__form_user_msg())
            self.conversation_extra.append(self.user_msg_extra)
            self.conversation_extra.append(self.user_msg_info_extra)
            self.user_msg = ""
            self.user_msg_info = {}
            self.user_msg_extra = {}
            self.user_msg_info_extra = {}

        if self.cody_msg is not None:
            # if cody_msg was stored before, save it and clear it
            self.conversation.append({
                'role': 'assistant',
                'content': str(self.cody_msg)
            })
            self.conversation_extra.append(self.cody_msg_extra)
            self.cody_msg = None
            self.cody_msg_extra = {}

    def __form_user_msg(self) -> list:
        """
        return standard type of user msg
        :return: dict
        """
        ret = [
            {
                "role": "system",
                "content": json.dumps(self.user_msg_info)
            },
            {
                "role": "user",
                "content": self.user_msg
            }
        ]

        return ret

    def update_action(self, action: str, id: int = None) -> int:
        """
        add an action declaration, which is supposed to be the description of command for Cody to understand.
        :param action: str, (e.g. remember a new name of somebody ("add_name": <name>))
        :param id: int (Optional), for update existed actions only
        :return: bool, status
        """
        if action in self.actions:
            id = self.actions.index(action)

        else:
            if id is not None and len(self.actions) >= id:
                self.actions[id] = action
            else:
                self.actions.append(action)
                id = len(self.actions) - 1

        return id

    def del_action(self, id: int = None, action_text: str = None):
        """
        delete an action
        :param id: int
        :param action_text: str
        :return:
        """
        if id is not None:
            self.actions.pop(id)

        elif action_text is not None:
            self.actions.remove(action_text)

    def update_extension(self, extension_text: str, id: int = None) -> int:
        """
        add or edit an extension of current preset
        :param extension_text: str, extension text
        :param id: int (Optional), if not set, then return a generated extension id
        :return: int, id
        """
        if extension_text in self.extensions:
            id = self.extensions.index(extension_text)

        else:
            if id is not None and len(self.extensions) >= id:
                self.extensions[id] = extension_text
            else:
                self.extensions.append(extension_text)
                id = len(self.extensions) - 1

        return id

    def del_extension(self, id: int = None, extension_text: str = None):
        """
        remove an extension text from current preset
        :param id: int
        :param extension_text: str
        :return:
        """
        if id is not None:
            self.extensions.pop(id)

        elif extension_text is not None:
            self.extensions.remove(extension_text)

    def update_conversation_example(self, examples: list = None, id: int = None) -> int:
        """
        add examples of conversation to demonstrate accurate response for Cody
        :param examples: list, list of dict of openai chat API
        :param id: int, start index of examples
        :return: int, id
        """
        if examples in self.conversation_examples:
            id = self.conversation_examples.index(examples)

        else:
            if id is not None and len(self.conversation_examples) >= id:
                self.conversation_examples[id] = examples
            else:
                self.conversation_examples.append(examples)
                id = len(self.conversation_examples) - 1

        return id

    def del_conversation_example(self, id: int = None, examples: dict = None):
        """
        delete a conversation example list
        :param id: int
        :param examples: str
        :return:
        """
        if id is not None:
            self.conversation_examples.pop(id)

        elif examples is not None:
            self.conversation_examples.remove(examples)

    def set_preset(self, basic: str):
        """
        set basic preset
        :param basic: str
        :return:
        """
        self.basic = basic

    def clear_conversation(self):
        """
        clear conversation in temporary memory, will not affect impressions
        :return:
        """
        self.conversation = []
        self.conversation_extra = []

    def to_json(self) -> dict:
        """
        return a dict object that can be directly parse by Preset
        :return: dict
        """
        res = {
            "basic": self.basic,
            "actions": self.actions,
            "extensions": self.extensions,
            "conversation_examples": self.conversation_examples,
            "conversation": self.conversation,
            "conversation_extra": self.conversation_extra,
            "max_token_limit": self.max_token_limit,
            "used_token_score": self.used_token_score
        }
        return res

    def add_user_message(self, msg: str, username: str, user_id: int, alternative_name: list = None,
                         timestamp: TimeStamp = None, extra_msg_info: dict = None):
        """
        add a new user message for conversation, but it will not be stored to "self.conversations"
        until next call or calling add_cody_message
        :param msg: str
        :param username: str
        :param user_id: int
        :param alternative_name: list
        :param timestamp: TimeStamp
        :param extra_msg_info: dict
        :return:
        """
        # set default values for empty arguments
        if alternative_name is None:
            alternative_name = []
        if timestamp is None:
            timestamp = TimeStamp(time.time())
        if extra_msg_info is None:
            extra_msg_info = {}

        # log
        self.__log("new user input: {}".format(msg))

        failed = True
        while failed:
            failed = False  # reset retry flag
            self.user_msg = msg  # form new user message to temp
            self.user_msg_info = {
                "message time": timestamp,
                "user ID": user_id,
                "name": username,
                "alternative names": alternative_name,
            }  # form new user message description to temp
            self.user_msg_info.update(extra_msg_info)  # update extra message info to temp

            # form new extra information for user_msg
            self.user_msg_extra = {
                "type": ExtraTypes.user_msg,
                "user_id": user_id,
                "username": username,
                "timestamp": timestamp
            }
            # form new extra information for user_msg_info
            self.user_msg_info_extra = {
                "type": ExtraTypes.user_msg_info,
                "user_id": user_id,
                "timestamp": timestamp
            }

            for func in self.user_msg_post_proc:
                # run additional function related to user message post-processing
                func()

            encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")  # initialize encoder

            # calculate token size of user_msg and user_msg_info
            user_msg_score = len(encoder.encode(json.dumps(self.user_msg_info)))
            user_msg_score += len(encoder.encode(self.user_msg))

            if self.used_token_score + user_msg_score >= self.max_token_limit:
                # if current token usage is going exceed, forget the oldest conversation segment
                del self.conversation[0]
                del self.conversation_extra[0]
                failed = True
                # log info
                self.__log("conversation token usage score exceeded max limit of {}, forcing to forget "
                           "the oldest conversation, current message segment count: {}".format(self.max_token_limit,
                                                                                               len(self.conversation)
                                                                                               ))

        # write message segment to conservation
        self.__save_and_clear_temp_msg()

    def add_cody_message(self, msg: GPTResponse):
        """
        add and process Cody's message from a GPTResponse.
        :param msg: GPTResponse
        :return:
        """
        self.cody_msg = msg  # copy message to temp

        # get last user_msg index(inverted)
        last_user_msg_index = -1
        for ele in self.conversation_extra[::-1]:
            if ele["type"] == ExtraTypes.user_msg:
                break
            last_user_msg_index -= 1

        self.cody_msg_extra = {
            "type": ExtraTypes.cody_msg,
            "user_id": self.conversation_extra[last_user_msg_index]["user_id"],
            "timestamp": self.conversation_extra[last_user_msg_index]["timestamp"]
        }

        for func in self.cody_msg_post_proc:
            # run additional functions that related to cody message's post-processing
            func()

        # log info
        self.__log("Cody feed back (raw): {}".format(msg))
        self.__log("token usage: {}".format(msg.usage))

        # write message segment to conservation
        self.__save_and_clear_temp_msg()

        # record token usage
        self.used_token_score = msg.usage.total_tokens

    def to_list(self) -> list:
        """
        generate conversation list that can be directly used by openai API
        :return: list
        """
        conversation_examples = []
        for ele in self.conversation_examples:
            conversation_examples.extend(ele)
        ret = [
            {"role": "system", "content": "{}\n"
                                          "You will include your feelings and actions of "
                                          "{} in JSON text format at the head of your message.\n"
                                          "{}".format(self.basic, ", ".join(self.actions), " ".join(self.extensions))},
            {"role": "system", "content": "*conversations of demonstration starts*"},
            *conversation_examples,
            {"role": "system", "content": "*Conversations of demonstration ends*"},
            *self.conversation
        ]

        return ret


if __name__ == '__main__':
    test_ps = Memory()
    a = test_ps.update_extension("This is a Demo of extension update.")
    b = test_ps.update_action("test action 001 [][][][]")
    b1 = test_ps.update_action("test action 002 [][][][]")
    b2 = test_ps.update_action("test action 001 [][][][]")
    c = test_ps.update_conversation_example([
        {"tetetetetetetetet": 123123},
        {"tetetetetete": 123123},
        {"te": 123123}
    ])

    c2 = test_ps.update_conversation_example([
        {"aaaaatetetetetetetetet": 123123},
        {"aaaatetetetetete": 123123},
        {"aaaate": 123123}
    ])

    c1 = test_ps.update_conversation_example([
        {"tetetetetetetetet": 123123},
        {"tetetetetete": 123123},
        {"te": 123123}
    ])

    print("\n".join([str(ele) for ele in test_ps.to_list()]))
    print("\n\n")
    a1 = test_ps.update_extension("Another demo of extension.")
    a = test_ps.update_extension("Changed Demo extension.", a)

    b2 = test_ps.update_action("test action 008 [][][][][][]", b2)

    c1 = test_ps.update_conversation_example([
        {"1230000321": 123123}
    ], c1)

    print("\n".join([str(ele) for ele in test_ps.to_list()]))
    print("\n\n")

    test_ps.del_action(b1)

    test_ps.del_extension(a1)

    test_ps.del_conversation_example(c1)

    print("\n".join([str(ele) for ele in test_ps.to_list()]))
    print("\n\n")

    print(test_ps.to_json())

    print("testing re-parsing in new Preset class: \n", Memory().parse_obj(test_ps.to_json()))
