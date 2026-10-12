#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡布西游脱机助手 —— 4399 登录态(auth_string)获取器。

供全链路测试(test_full_link.py)与定时任务使用：
  1. 优先使用本地凭证 credentials.json 中的 token（已登录态，直接复用）
  2. 其次使用凭证中的 cookie（Uauth/Pauth/Xauth），走 4399 checkKidLoginUserCookie
     换取游戏 auth_string（与 get_auth_string.py 同链路）
  3. 最后尝试账号密码走 ptlogin 表单登录（若 4399 风控/验证码拦截会失败，
     此时需手动在浏览器登录后把 cookie/token 写入 credentials.json）

安全约定：本文件绝不把账号、密码、cookie 写入日志/仓库；
凭证文件 credentials.json 已被 .gitignore 排除，永不上传。
"""
import argparse
import http.cookiejar
import json
import os
import sys
import time
import urllib.parse
import urllib.request

# ---- 与 get_auth_string.py / base.py 保持一致的常量 ----
CHECK_KID_URL = (
    "http://ptlogin.4399.com/ptlogin/checkKidLoginUserCookie.do?"
    "appId=kabu_xy&level=8&loginLevel=8&regLevel=8&bizId=1202000651&canBack=true"
    "&gameUrl=http%3A%2F%2Fenter.wanwan4399.com%2Fbin-debug%2FKBgameindex.html"
    "&css=&onLineStart=false&retUrl={ret}"
)
LOGIN_PAGE_URL = "https://ptlogin.4399.com/ptlogin/login.do?v=1"
LOGIN_FORM_URL = "https://ptlogin.4399.com/ptlogin/loginForm.do"
CRED_FILE = "credentials.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
      "Chrome/101.0.9999.0 Safari/537.36")


def _cred_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CRED_FILE)


def load_credentials() -> dict:
    try:
        with open(_cred_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def save_credentials(data: dict) -> None:
    with open(_cred_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # 不跟随重定向，从 302 Location 取 auth_string


def cookie_to_auth_string(cookie: str, timeout: float = 15) -> str:
    """带 cookie 请求 checkKidLoginUserCookie.do，从 302 Location 提取 auth_string。"""
    v = str(int(time.time() * 1000))
    ret = urllib.parse.quote(
        "http://news.4399.com/login/kbxy.html?reg=0&pass=1&v=" + v, safe="")
    url = CHECK_KID_URL.format(ret=ret)
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "http://news.4399.com/",
        "Cookie": cookie,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    try:
        opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location")
        if not loc:
            raise RuntimeError(f"checkKidLoginUserCookie 无 Location(HTTP {e.code})，cookie 可能已过期")
    else:
        raise RuntimeError("checkKidLoginUserCookie 未重定向，cookie 无效")
    auth = loc.split("?", 1)[1] if "?" in loc else loc
    if not auth:
        raise RuntimeError("auth_string 为空")
    return auth


def password_login(username: str, password: str, timeout: float = 15) -> str:
    """尝试账号密码登录 4399，返回可用的 cookie 串。

    4399 表单登录受验证码/风控影响较大，失败会抛 RuntimeError；
    调用方可回退到手动 cookie 路径。
    """
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    # 1) 打开登录页拿会话与隐藏参数
    try:
        page = opener.open(urllib.request.Request(
            LOGIN_PAGE_URL, headers={"User-Agent": UA, "Referer": "http://news.4399.com/"}), timeout=timeout).read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"打开登录页失败: {e}")
    # 2) 常见隐藏字段（缺省值）
    form = {
        "user": username,
        "pass": password,
        "v": "1",
        "appId": "kabu_xy",
        "bizId": "1202000651",
        "displayMode": "popup",
        "postLoginHandler": "default",
        "redirectUrl": "",
    }
    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(LOGIN_FORM_URL, data=data, headers={
        "User-Agent": UA,
        "Referer": LOGIN_PAGE_URL,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    try:
        resp = opener.open(req, timeout=timeout)
        final_url = resp.geturl()
        resp.read()
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "")
        final_url = loc or ""
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"提交登录失败: {e}")
    cookies = []
    for c in opener.handlers:
        if hasattr(c, "cookiejar") and hasattr(c.cookiejar, "make_cookies"):
            try:
                cookies = [x.name + "=" + x.value for x in c.cookiejar]
            except Exception:  # noqa: BLE001
                cookies = []
    if not cookies:
        # opener 未启用 cookiejar：直接从响应头收集
        raise RuntimeError("未取得登录 cookie（可能触发验证码/风控），请改用手动 cookie 路径")
    if "login" in final_url and "success" not in final_url:
        raise RuntimeError("登录未成功，请检查账号密码或改用手动 cookie 路径")
    return "; ".join(cookies)


def get_token(cred: dict, save: bool = False) -> str:
    """按优先级取 auth_string：token > cookie > 账号密码。"""
    token = (cred.get("token") or "").strip()
    if token:
        return token
    cookie = (cred.get("cookie") or "").strip()
    if cookie:
        auth = cookie_to_auth_string(cookie)
        if save:
            cred["token"] = auth
            cred["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_credentials(cred)
        return auth
    user = (cred.get("username") or "").strip()
    pwd = cred.get("password") or ""
    if user and pwd:
        ck = password_login(user, pwd)
        auth = cookie_to_auth_string(ck)
        if save:
            cred["cookie"] = ck
            cred["token"] = auth
            cred["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_credentials(cred)
        return auth
    raise RuntimeError("credentials.json 缺少 token/cookie/账号密码，无法取登录态")


def main() -> int:
    ap = argparse.ArgumentParser(description="4399 登录态获取器")
    ap.add_argument("--user", default="", help="4399 账号")
    ap.add_argument("--pass", dest="password", default="", help="4399 密码")
    ap.add_argument("--cookie", default="", help="已登录 cookie（优先于账号密码）")
    ap.add_argument("--token", default="", help="已有 auth_string（最高优先）")
    ap.add_argument("--save", action="store_true", help="把结果写回 credentials.json")
    ap.add_argument("--cred-file", default="", help="自定义凭证文件路径")
    args = ap.parse_args()

    global CRED_FILE
    if args.cred_file:
        CRED_FILE = args.cred_file
    cred = load_credentials()
    if args.user:
        cred["username"] = args.user
    if args.password:
        cred["password"] = args.password
    if args.cookie:
        cred["cookie"] = args.cookie
    if args.token:
        cred["token"] = args.token
    try:
        auth = get_token(cred, save=args.save)
    except Exception as e:  # noqa: BLE001
        print(f"[LOGIN-ERR] {e}", file=sys.stderr)
        print("提示：在浏览器登录卡布西游后，把 Cookie(含Uauth/Pauth/Xauth)写入 credentials.json 的 cookie 字段，再重试。")
        return 2
    print(auth)  # 仅输出 auth_string，不输出账号/密码/cookie
    return 0


if __name__ == "__main__":
    sys.exit(main())
