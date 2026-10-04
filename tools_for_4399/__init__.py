# -*- coding: utf-8 -*-
"""4399 —— 4399 / 卡布西游 工具库。

模块划分：
  base            基础方法：AES密码加密 / 账号本地存储 / 平台常量
  kbxy            卡布西游网关客户端：KabuClient + 协议/opcode
  kbxy_standalone 成品函数：login_4399 / get_auth_string / enter_server / kabu_login

快捷用法：
    from 4399 import kabu_login
    player_id, server_id = kabu_login("账号", "密码", server_mode="random")
"""
from . import base, kbxy  # noqa: F401
from .kbxy_standalone import (enter_server, get_auth_string, kabu_login,  # noqa: F401
                              login_4399)

__version__ = "0.1.0"
__all__ = ["base", "kbxy", "login_4399", "get_auth_string", "enter_server", "kabu_login"]
