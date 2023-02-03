#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: config.py
# Created on: 2022/12/27

import yaml
import json
from pathlib import Path
from pydantic import BaseSettings
from nonebot import get_driver
from nonebot.rule import to_me
from nonebot.log import logger


class Config(BaseSettings):

    cody_session_cache_path: str = "cache/session.json"
    cody_gpt3_apikey_path: str = "configs/gpt3_api.yml"
    cody_gpt3_max_tokens: int = 400
    cody_max_session_tokens: int = 2048
    cody_session_forget_timeout: int = 3600
    cody_initial_mad_level_change_time_span: int = 600
    cody_mad_level_speedup_gamma: float = 0.7
    cody_mad_level_release_rate: float = 0.3
    cody_mad_level_change_msg_count_threshold: int = 5

    class Config:
        extra = "ignore"


DRIVER = get_driver()
global_config = DRIVER.config
CODY_CONFIG = Config.parse_obj(global_config)

# 创建路径
LOCAL_CONFIG = Path() / "configs"
LOCAL_CONFIG.mkdir(exist_ok=True)
if not Path(CODY_CONFIG.cody_gpt3_apikey_path).exists():
    with open(CODY_CONFIG.cody_gpt3_apikey_path, 'w', encoding='utf-8') as f:
        yaml.dump({"api_keys": []}, f, allow_unicode=True)
        f.close()

# 创建路径
LOCAL_CACHE = Path() / "cache"
LOCAL_CACHE.mkdir(exist_ok=True)
if not Path(CODY_CONFIG.cody_session_cache_path).exists():
    with open(CODY_CONFIG.cody_session_cache_path, 'w', encoding='utf-8') as f:
        f.close()

# 读取api密钥
with open(CODY_CONFIG.cody_gpt3_apikey_path, 'r', encoding='utf-8') as f:
    APIKEY_LIST = yaml.load(f, Loader=yaml.FullLoader).get('api_keys')

logger.info(f"加载 {len(APIKEY_LIST)}个 APIKeys")
