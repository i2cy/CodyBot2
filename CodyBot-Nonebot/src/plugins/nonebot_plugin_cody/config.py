#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: config.py
# Created on: 2022/12/27

import yaml
from pathlib import Path
from pydantic import BaseSettings
from nonebot import get_driver
from nonebot.rule import to_me
from nonebot.log import logger


class Config(BaseSettings):
    # Your Config Here
    gpt3_api_key_path: str = "configs/gpt3_api.yml"
    gpt3_command_prefix: str = '.'
    gpt3_need_at: bool = False
    gpt3_image_render: bool = False
    gpt3_image_limit: int = 100
    gpt3_max_tokens: int = 400
    gpt3_max_session_tokens: int = 2048

    class Config:
        extra = "ignore"


driver = get_driver()
global_config = driver.config
config = Config.parse_obj(global_config)

gpt3_api_key_path = config.gpt3_api_key_path
gpt3_command_prefix = config.gpt3_command_prefix
gpt3_need_at = config.gpt3_need_at
gpt3_image_render = config.gpt3_image_render
gpt3_image_limit = config.gpt3_image_limit
gpt3_max_tokens = config.gpt3_max_tokens
gpt3_max_session_tokens = config.gpt3_max_session_tokens

# 如果不存在则创建
LOCAL = Path() / "configs"
LOCAL.mkdir(exist_ok=True)
if not Path(gpt3_api_key_path).exists():
    with open(gpt3_api_key_path, 'w', encoding='utf-8') as f:
        yaml.dump({"api_keys": []}, f, allow_unicode=True)

with open(gpt3_api_key_path, 'r', encoding='utf-8') as f:
    api_key_list = yaml.load(f, Loader=yaml.FullLoader).get('api_keys')


logger.info(f"加载 {len(api_key_list)}个 APIKeys")

# 基本会话
matcher_params = {'cmd': gpt3_command_prefix}
if gpt3_need_at:
    matcher_params['rule'] = to_me()

# 其他命令
need_at = {}
if gpt3_need_at:
    need_at['rule'] = to_me()
