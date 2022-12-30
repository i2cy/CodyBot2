<!-- markdownlint-disable MD033 MD036 MD041 -->

<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# OpenAI bot: Cody

*Based on Nonebot & Mirai2*

_✨ [Codybot2 查看机器人](https://github.com/i2cy/CodyBot2) ✨_

</div>

<p align="center">
  <a href="https://github.com/i2cy/Nonebot-Plugin-LockingLock/master/LICENSE">
    <img src="https://img.shields.io/github/license/i2cy/Nonebot-Plugin-LockingLock.svg" alt="license">
  </a>
  <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="python">
</p>

## 简介
这是一个私人项目，但其中的内容欢迎大家参考、移植。

机器人的对话机制默认为连续对话，拥有一定的会话记忆能力，同时对私聊、
群聊有着不同的反应适配，能够很好的处理多人对话时的逻辑、人名等等。

Cody是一只可爱的小马，Icy是她的创造者，由此Cody非常尊重Icy。

## 特性
 - Cody的记忆在同一个群聊中是使用的同一个记忆空间，在私聊中每个人都是
   单独的一个记忆空间，意思是群聊中的内容，在私聊里Cody不一定记得
 - Cody的记忆拥有遗忘机制，超过特定时间的对话句子会被自动遗忘，以节省
   API tokens的消耗开支
 - Cody默认情况下在扣扣qun的对话中，会以各位的群昵称称呼，在私聊中则
   以备注或昵称称呼，对Icy及其它特殊人物会以本名称呼
 - Cody拥有一定的情绪机制，当对话频率超过一定阈值的时候会感到疲惫，倘
   若继续对话，会使得Cody怠惰，甚至生气，开始辱骂尝试与她聊天的人（从
   而节省tokens开支）

## 配置项

配置方式：直接在 NoneBot 全局配置文件中添加以下配置项即可。

### 默认配置模板
    ENVIRONMENT=dev
    VERIFY_KEY=Your_key_here                     # MiraiApiHttp2 配置文件里的 token
    driver=~fastapi+~websockets                  # nonebot_adapter_mirai2 需要使用 websockets 驱动所以需要加该行
    
    MIRAI_HOST=127.0.0.1                         # MiraiApiHttp2 的 ip
    MIRAI_PORT=5700                              # MiraiApiHttp2 的端口
    MIRAI_QQ=["0123456789"]                      # Mirai 上已经登录的 qq 号
    SUPERUSER=["2222222222"]                     # nonebot2 的超管(也可理解为bot的主人什么的)
    
    gpt3_api_key_path = "configs/gpt3_api.yml"          # api文件的路径
    gpt3_command_prefix = "cody"                        # 基本会话中的指令前缀
    gpt3_need_at = False                                # 是否需要@才触发命令
    gpt3_image_render = False                           # 是否渲染为图片
    gpt3_image_limit = 100                              # 长度超过多少才会渲染成图片
    gpt3_max_tokens = 250                               # 最大返回值长度
    gpt3_max_session_tokens = 1000                      # 最大连续对话长度
    gpt3_session_forget_timeout = 10800                 # 会话从多少秒后开始忘记
    gpt3_cody_initial_mad_level_change_time_span = 600  # Cody情绪检测时间跨度（秒）
    gpt3_cody_mad_level_speedup_gamma = 0.7             # 愤怒加速指数（越小越快）
    gpt3_cody_mad_level_release_rate = 0.3              # 愤怒减轻比例（越小越不容易恢复）
    gpt3_cody_mad_level_change_msg_count_threshold = 25 # 在检测时间跨度内的消息数量超过此阈值时改变情绪
