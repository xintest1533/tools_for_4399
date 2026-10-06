# -*- coding: utf-8 -*-
"""一次性激活授权核心：RSA 签名卡密（防伪造）+ 机器码绑定 + 有效期 + 规格 + 云端时间校验。"""
import base64
import hashlib
import hmac
import re
import time
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import requests
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

import auth

TIER_MAP = {"full": "FULL", "cultivate": "CULTURE"}
DUR_MAP = {"1": "1D", "7": "7D", "365": "365D", "per": "PER"}
DUR_DAYS = {"1": 1, "7": 7, "365": 365}
CARD_TYPES = {
    "CULTURE-1D", "CULTURE-7D", "CULTURE-365D", "CULTURE-PER",
    "FULL-1D", "FULL-7D", "FULL-365D", "FULL-PER",
}
# 客户端仅含公钥：能验签、不能伪造卡密（私钥只在作者端 key_private.py）。
RSA_PUB_PEM = (
    "-----BEGIN PUBLIC KEY-----\n"
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAm11HlpL7/hN0xteZpD38\n"
    "8wlIw7J8/rVPUt5t2bchmNNLmNQlGZDR62QIRXd2ICZudwngDw7VUG00kKOv63yO\n"
    "EL55EkdnDH445zkKwUrqTGAmMr0qjqg0upfYo+RpAEFfO3Pq3BVk1oz5+76jlKpV\n"
    "3wquJXlPzECpSEh3CXcjxxgTdc7bC6R1LqoW3XHlQ4JDINq+lXj0i7ZzPe1cfYFY\n"
    "XqXU5DWmMsUy2KizwUsaAz9mi61wr5OnxBY3AXfzH/95DQPFJvE78tUP9+3e57tv\n"
    "K5O3FVwQ4jnRVQct7P/OYEgSkiBX7ndzZCP2eyc0Wae1Zkf2jNAsGpovfuy301qg\n"
    "/wIDAQAB\n"
    "-----END PUBLIC KEY-----"
)
_CARD_RE = re.compile(
    r"^KABU-([A-Z]+-\d+D|FULL-PER|CULTURE-PER)-(\d{8})-([A-Za-z0-9_\-]+)$",
    re.IGNORECASE)
# 同步 auth 档位表，令 check_license / write_license 认新档位
auth.CARD_TYPES = CARD_TYPES


def get_machine_code(mac=None):
    """由 MAC（AA:BB:..或AA-BB-..）派生绑定码；缺省用本机。"""
    if mac:
        mac_hex = mac.replace(":", "").replace("-", "").upper()
        return hashlib.md5(mac_hex.encode("ascii")).hexdigest().upper()
    return auth.get_machine_code()


def _sign(priv_pem, mc, card_type, date):
    """用作者私钥对 (机器码|规格|日期) 签名。"""
    key = RSA.import_key(priv_pem)
    h = SHA256.new(("%s|%s|%s" % (mc, card_type, date)).encode("ascii"))
    sig = pkcs1_15.new(key).sign(h)
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def gen_card(mac, tier, duration, priv_pem):
    """作者端生成卡密（需私钥）。tier=full/cultivate，duration=1/7/365/per。返回 (card, card_type, expire)。"""
    tier = str(tier).strip().lower()
    dur = str(duration).strip().lower()
    if tier not in TIER_MAP:
        raise ValueError("规格必须为 full 或 cultivate")
    if dur not in DUR_MAP:
        raise ValueError("有效期必须为 1 / 7 / 365 / per")
    card_type = "%s-%s" % (TIER_MAP[tier], DUR_MAP[dur])
    expire = datetime(2099, 12, 31) if dur == "per" else datetime.now() + timedelta(days=DUR_DAYS[dur])
    mc = get_machine_code(mac)
    date = expire.strftime("%Y%m%d")
    sig = _sign(priv_pem, mc, card_type, date)
    return "KABU-%s-%s-%s" % (card_type, date, sig), card_type, expire


def parse_card(card):
    m = _CARD_RE.fullmatch(str(card).strip())
    if not m:
        return None
    card_type, expiry, sig_b64 = m.group(1).upper(), m.group(2), m.group(3)
    try:
        expire = datetime.strptime(expiry, "%Y%m%d")
    except ValueError:
        return None
    return card_type, expire, sig_b64


def verify_card(card, mac=None):
    """客户端公钥验签：格式/规格/有效期/MAC绑定。返回 (ok, card_type, expire)。"""
    p = parse_card(card)
    if not p:
        return False, "", None
    card_type, expire, sig_b64 = p
    if expire.date() < datetime.now().date():
        return False, card_type, expire
    mc = get_machine_code(mac)
    sig = base64.urlsafe_b64decode(sig_b64 + "=" * ((4 - len(sig_b64) % 4) % 4))
    pub = RSA.import_key(RSA_PUB_PEM)
    h = SHA256.new(("%s|%s|%s" % (mc, card_type, expire.strftime("%Y%m%d"))).encode("ascii"))
    try:
        pkcs1_15.new(pub).verify(h, sig)
        return True, card_type, expire
    except (ValueError, TypeError):
        return False, card_type, expire


def activate(card, mac=None):
    """激活：公钥验签通过则写注册表。返回 (ok, msg)。"""
    mac = mac or auth.get_mac()
    ok, card_type, expire = verify_card(card, mac)
    if not ok:
        return False, "卡密无效、已过期或与当前机器不匹配"
    auth.write_license(card_type, expire)
    return True, "激活成功"


# 可逆机器码：MAC 异或混淆 + 校验字节 -> base32，生成器可解密还原 MAC。
_KEY = bytes([0x5A, 0xC3, 0x1F, 0x9B, 0x77, 0xE4, 0x2D, 0x81])


def mac_to_code(mac):
    """MAC -> 可逆机器码（加密所得，生成器可解密还原 MAC）。"""
    hexs = mac.replace(":", "").replace("-", "").upper()
    b = bytes.fromhex(hexs)
    x = bytes(b[i] ^ _KEY[i % len(_KEY)] for i in range(6))
    raw = x + bytes([sum(x) % 256])
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def code_to_mac(code):
    """机器码 -> 还原 MAC；校验失败抛 ValueError。"""
    pad = code.strip().upper()
    pad += "=" * ((8 - len(pad) % 8) % 8)
    raw = base64.b32decode(pad)
    if len(raw) != 7:
        raise ValueError("机器码格式错误")
    x, cksum = raw[:-1], raw[-1]
    if sum(x) % 256 != cksum:
        raise ValueError("机器码校验失败")
    b = bytes(x[i] ^ _KEY[i % len(_KEY)] for i in range(6))
    return ":".join("%02X" % c for c in b)


# 防时间戳绕过：向云端请求时间，对比系统时间。
_TIME_URLS = ("https://www.baidu.com", "https://www.qq.com", "http://enter.wanwan4399.com")


def fetch_remote_timestamp(timeout=5):
    """从云端响应 Date 头取时间戳；全部失败抛 RuntimeError。"""
    for u in _TIME_URLS:
        try:
            r = requests.get(u, timeout=timeout)
            h = r.headers.get("Date")
            if h:
                ts = parsedate_to_datetime(h).timestamp()
                if ts:
                    return ts
        except Exception:
            continue
    raise RuntimeError("无法获取远端时间")


def verify_system_time(tolerance=300):
    """对比系统时间与云端时间。返回 (ok, msg)。"""
    try:
        remote = fetch_remote_timestamp()
    except Exception:
        return False, "请连接互联网"
    if abs(remote - time.time()) > tolerance:
        return False, "请修正系统时间"
    return True, ""
