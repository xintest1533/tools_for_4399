# -*- coding: utf-8 -*-
"""4399.base —— 第一类：基础方法。

提供与平台无关的通用工具，供上层模块复用：
  - 4399 密码 AES 加密（encrypt_password）
  - 登录/认证所需常量
  - 本地账号库存储（load/save/upsert/remove/get_last 等）

注意：本模块不含任何游戏协议细节，也不含任何账号密码硬编码。
"""
import hashlib
import json
import os
import base64
import time
from datetime import datetime

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ---------- 4399 平台常量 ----------
PASSPHRASE = "lzYW5qaXVqa"
LOGIN_FRAME_URL = "https://ptlogin.4399.com/ptlogin/loginFrame.do"
LOGIN_URL = "https://ptlogin.4399.com/ptlogin/login.do?v=1"
HTTP_TIMEOUT = (3, 8)
LOGIN_FRAME_PARAMS = {
    "postLoginHandler": "default",
    "redirectUrl": "",
    "displayMode": "popup",
    "css": "",
    "bizId": "1202000651",
    "appId": "kabu_xy",
    "gameId": "",
    "level": "8",
    "regLevel": "8",
    "externalLogin": "qq",
}

# ---------- 账号本地存储 ----------
ACCOUNTS_FILE = "accounts.json"


def _accounts_path():
    # 优先跟随当前工作目录，其次包所在目录，保证 pip 安装后也能写入
    cwd = os.path.join(os.getcwd(), ACCOUNTS_FILE)
    pkg = os.path.join(os.path.dirname(os.path.abspath(__file__)), ACCOUNTS_FILE)
    return cwd if os.access(os.path.dirname(cwd), os.W_OK) else pkg


def _default_cfg() -> dict:
    return {"auto_login": False, "accounts": []}


def load_accounts() -> dict:
    """加载账号库配置；损坏或缺失时返回空配置。"""
    try:
        with open(_accounts_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_cfg()
        data.setdefault("auto_login", False)
        data.setdefault("accounts", [])
        if not isinstance(data["accounts"], list):
            data["accounts"] = []
        clean = []
        for a in data["accounts"]:
            if not isinstance(a, dict) or not a.get("username"):
                continue
            clean.append({
                "username": str(a["username"]),
                "password": a.get("password", ""),
                "remember": bool(a.get("remember", False)),
                "last_used": a.get("last_used", 0),
            })
        data["accounts"] = clean
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return _default_cfg()


def save_accounts(data: dict) -> None:
    with open(_accounts_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_accounts(data: dict) -> list:
    """账号用户名列表（最近使用优先）。"""
    return [a["username"] for a in sorted(
        data["accounts"], key=lambda x: x.get("last_used", 0), reverse=True)]


def find_account(data: dict, username: str):
    for a in data["accounts"]:
        if a["username"] == username:
            return a
    return None


def upsert_account(data: dict, username: str, password: str = "", remember: bool = False) -> None:
    a = find_account(data, username)
    if a is None:
        data["accounts"].append({
            "username": username, "password": password if remember else "",
            "remember": remember, "last_used": int(time.time()),
        })
    else:
        if remember:
            a["password"] = password
            a["remember"] = True
        a["last_used"] = int(time.time())


def touch_account(data: dict, username: str) -> None:
    a = find_account(data, username)
    if a is not None:
        a["last_used"] = int(time.time())


def remove_account(data: dict, username: str) -> None:
    data["accounts"] = [a for a in data["accounts"] if a["username"] != username]


def get_last_account(data: dict):
    """最近使用且记住密码的账号；无则 None。"""
    for a in sorted(data["accounts"], key=lambda x: x.get("last_used", 0), reverse=True):
        if a.get("remember"):
            return a
    return None


# ---------- 密码加密 ----------
def _evp_bytes_to_key(password, salt, key_len=32, iv_len=16):
    dt = b""
    d = b""
    while len(d) < key_len + iv_len:
        dt = hashlib.md5(dt + password + salt).digest()
        d += dt
    return d[:key_len], d[key_len:key_len + iv_len]


def encrypt_password(password: str) -> str:
    """4399 登录密码 AES-128-CBC 加密，OpenSSL Salted__ 格式。"""
    salt = os.urandom(8)
    key, iv = _evp_bytes_to_key(PASSPHRASE.encode(), salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(password.encode("utf-8"), AES.block_size))
    return base64.b64encode(b"Salted__" + salt + encrypted).decode("utf-8")
