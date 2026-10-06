
import re
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urljoin, urlsplit

import requests

from .base import (encrypt_password, HTTP_TIMEOUT, LOGIN_FRAME_URL, LOGIN_FRAME_PARAMS,
                   LOGIN_URL)
from .kbxy import HOST, KabuClient

AUTH_ENDPOINT = "http://ptlogin.4399.com/ptlogin/checkKidLoginUserCookie.do"
GAME_URL = "http://enter.wanwan4399.com/bin-debug/KBgameindex.html"
APP_ID = "kabu_xy"
BIZ_ID = "1202000651"

__all__ = ["login_4399", "get_auth_string", "enter_server", "kabu_login"]

class _LoginFormParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.action = ""
        self.fields = {}
        self._in_login_form = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            if not self.action and attributes.get("action"):
                self.action = attributes["action"]
                self._in_login_form = True
            return
        if tag != "input" or not self._in_login_form:
            return
        name = attributes.get("name")
        if not name:
            return
        input_type = attributes.get("type", "text").lower()
        if input_type == "checkbox":
            if "checked" not in attributes:
                return
            self.fields[name] = attributes.get("value", "on")
        elif input_type not in ("submit", "button", "reset", "file", "image"):
            self.fields[name] = attributes.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form" and self._in_login_form:
            self._in_login_form = False

def _parse_login_form(html: str, base_url: str):
    parser = _LoginFormParser()
    parser.feed(html)
    if not parser.action:
        raise RuntimeError("4399登录框响应中未找到登录表单")
    action = urljoin(base_url, parser.action)
    parsed = urlsplit(action)
    if (parsed.scheme != "https" or parsed.hostname != "ptlogin.4399.com"
            or parsed.path != "/ptlogin/login.do"
            or parse_qs(parsed.query).get("v") != ["1"]):
        raise RuntimeError("4399登录框返回了不受支持的认证地址")
    if not {"username", "password"} - parser.fields.keys():
        return action, parser.fields
    raise RuntimeError("4399登录表单缺少账号或密码字段")

def login_4399(username: str, password: str, log=None) -> dict:
    cb = log or (lambda m: None)
    if not username or not password:
        raise ValueError("账号和密码不能为空")

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    })
    cb("正在加载4399登录框并获取本次会话参数")
    resp = s.get(LOGIN_FRAME_URL, params={**LOGIN_FRAME_PARAMS, "username": username},
                 timeout=HTTP_TIMEOUT, allow_redirects=False)
    resp.raise_for_status()

    login_url, data = _parse_login_form(resp.text, resp.url)
    data["username"] = username
    data["password"] = encrypt_password(password)
    s.headers.update({"Origin": "https://ptlogin.4399.com", "Referer": resp.url})
    cb("正在提交4399认证请求")
    auth_resp = s.post(login_url, data=data, timeout=HTTP_TIMEOUT, allow_redirects=False)
    auth_resp.raise_for_status()

    cookies = dict(s.cookies)
    cookies.update(auth_resp.cookies)
    if "Pauth" not in cookies:
        raise RuntimeError(f"4399登录失败，未收到 Pauth (HTTP {auth_resp.status_code})")
    cb(f"4399登录成功，获取Cookie {len(cookies)} 个")
    return cookies

def get_auth_string(cookies: dict, level: int = 8, log=None) -> str:
    cb = log or (lambda m: None)
    v = str(int(time.time() * 1000))
    ret = quote(f"http://news.4399.com/login/kbxy.html?reg=0&pass=1&v={v}", safe="")
    url = (f"{AUTH_ENDPOINT}?appId={APP_ID}&level={level}&loginLevel={level}"
           f"&regLevel={level}&bizId={BIZ_ID}&canBack=true"
           f"&gameUrl={quote(GAME_URL, safe='')}&css=&onLineStart=false&retUrl={ret}")
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = requests.Request("GET", url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) "
                      "AppleWebKit/537.36 Chrome/101.0.9999.0 Safari/537.36",
        "Referer": "http://news.4399.com/",
        "Cookie": cookie_str,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    prepared = req.prepare()
    sess = requests.Session()
    resp = sess.send(prepared, timeout=HTTP_TIMEOUT, allow_redirects=False)
    if resp.status_code not in (301, 302, 303, 307, 308):
        raise RuntimeError(f"auth接口返回 {resp.status_code}，非重定向；Cookie 可能已失效")
    loc = resp.headers.get("Location", "")
    if "?" not in loc:
        raise RuntimeError("auth接口 Location 缺少 auth_string")
    auth = loc.split("?", 1)[1]
    if "sig=" not in auth:
        raise RuntimeError("auth_string 缺少 sig 字段")
    cb(f"获取 auth_string 成功 (len={len(auth)})")
    return auth

def enter_server(auth_string: str, server_id: int = None, server_mode: str = "auto",
                 log=None):

    client = KabuClient(HOST, log_callback=log or print)
    client.connect()
    client.login(auth_string, timeout=30, server_id=server_id, server_mode=server_mode)
    return client

def kabu_login(username: str, password: str, server_id: int = None,
               server_mode: str = "auto", log=None):

    cb = log or (lambda m: None)
    cookies = login_4399(username, password, log=cb)
    auth = get_auth_string(cookies, log=cb)
    client = enter_server(auth, server_id, server_mode, log=cb)
    return client.user_id, client.selected_server_id
